// ===== 全局变量 =====
let currentSearchType = 'web';
let currentSearchResults = null;
let currentKeyword = '';
let analysisResult = null;
let originalUserInput = '';
let uploadMode = false;
let sidebarVisible = true;

// 自动确认相关的计时器
let autoConfirmTimer = null;
let autoFilterTimer = null;
let autoCrawlTimer = null;




// 【新增】用于存储视频高级设置的全局对象
let videoAdvancedSettings = {
    duration: 'medium',
    voice: 'female',        // 默认值
    voiceFile: null,        // 用于存储上传的语音文件
    voiceText: '', // 【新增】用于存储自定义的文本
    background: 'background.png',  // 默认值
    backgroundFile: null    // 用于存储上传的背景文件
};
// 【修改】使用一个更强大的对象来追踪当前的播放状态
let currentPreview = {
    audio: null,      // 存储Audio对象
    button: null,     // 存储正在播放的那个按钮元素
};

// DOM元素缓存
const elements = {};

// ===== 应用程序初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    initializeEventListeners();
    loadContentList();
    initializeSidebar();
    // 页面加载完成后初始化文件分组状态
    setTimeout(initFileGroupStates, 100);
});

// 缓存DOM元素
function initializeElements() {
    elements.searchInput = document.getElementById('searchInput');
    elements.searchBtn = document.getElementById('searchBtn');
    elements.functionToggle = document.getElementById('functionToggle');
    elements.functionDropdown = document.getElementById('functionDropdown');
    elements.loading = document.getElementById('loading');
    elements.analysisCard = document.getElementById('analysisCard');
    elements.resultsCard = document.getElementById('resultsCard');
    elements.sidebar = document.getElementById('sidebar');
    elements.sidebarOverlay = document.getElementById('sidebarOverlay');
    elements.sidebarToggle = document.getElementById('sidebarToggle');
    elements.previewModal = document.getElementById('previewModal');
    elements.pdfFileInput = document.getElementById('pdfFileInput');
}

// 初始化事件监听器
// ===== 【7.21 14:22修改setting】初始化事件监听器 =====
function initializeEventListeners() {
    // 功能菜单切换
    elements.functionToggle.addEventListener('click', toggleFunctionMenu);
    
    // 功能选项选择
    document.querySelectorAll('.function-option').forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            if (option.dataset.type) {
                switchSearchType(option.dataset.type);
            }
            closeFunctionMenu();
        });
    });

    // 点击外部关闭菜单
    document.addEventListener('click', (e) => {
        if (!elements.functionToggle.contains(e.target) && !elements.functionDropdown.contains(e.target)) {
            closeFunctionMenu();
        }
    });

    // 搜索功能
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    // 分析结果按钮
    const confirmSearchBtn = document.getElementById('confirmSearchBtn');
    const modifyKeywordBtn = document.getElementById('modifyKeywordBtn');
    const cancelAnalysisBtn = document.getElementById('cancelAnalysisBtn');
    
    if (confirmSearchBtn) confirmSearchBtn.addEventListener('click', confirmAndSearch);
    if (modifyKeywordBtn) modifyKeywordBtn.addEventListener('click', modifyKeyword);
    if (cancelAnalysisBtn) cancelAnalysisBtn.addEventListener('click', cancelAnalysis);

    // 筛选结果按钮
    const confirmFilterBtn = document.getElementById('confirmFilterBtn');
    const cancelFilterBtn = document.getElementById('cancelFilterBtn');
    
    if (confirmFilterBtn) confirmFilterBtn.addEventListener('click', confirmFilter);
    if (cancelFilterBtn) cancelFilterBtn.addEventListener('click', cancelFilter);

    // 模态框关闭
    elements.previewModal.addEventListener('click', function(e) {
        if (e.target === this) {
            closePreview();
        }
    });

    // 侧栏遮罩层点击关闭
    elements.sidebarOverlay.addEventListener('click', function() {
        if (sidebarVisible) {
            toggleSidebar();
        }
    });

    // ESC键关闭模态框和侧栏
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePreview();
            if (sidebarVisible) {
                toggleSidebar();
            }
        }
    });

    // 响应式处理
    window.addEventListener('resize', handleResize);




    // ... 其他所有事件监听器保持不变 ...
    // 【新增】监听输出格式下拉框的变动
    const outputFormatSelect = document.getElementById('outputFormatSelect');
    if (outputFormatSelect) {
        outputFormatSelect.addEventListener('change', handleOutputFormatChange);
        // 页面加载时立即调用一次，以设置初始状态
        handleOutputFormatChange(); 
    }

    // 【新增】监听打开视频高级设置按钮的点击事件
    const openVideoSettingsBtn = document.getElementById('openVideoSettingsBtn');
    if (openVideoSettingsBtn) {
        openVideoSettingsBtn.addEventListener('click', openVideoSettingsModal);
    }
    // =====over======
}

// ===== 功能菜单管理 =====
function toggleFunctionMenu() {
    const isOpen = elements.functionDropdown.classList.contains('show');
    if (isOpen) {
        closeFunctionMenu();
    } else {
        openFunctionMenu();
    }
}

function openFunctionMenu() {
    elements.functionDropdown.classList.add('show');
    elements.functionToggle.classList.add('active');
}

function closeFunctionMenu() {
    elements.functionDropdown.classList.remove('show');
    elements.functionToggle.classList.remove('active');
}

// ===== 搜索功能 =====
function switchSearchType(type) {
    currentSearchType = type;
    
    // 如果当前在上传模式，切换回搜索模式
    if (uploadMode) {
        switchToUploadMode(); // 这会切换回搜索模式
    }
    
    // 更新选项状态
    document.querySelectorAll('.function-option').forEach(option => {
        option.classList.remove('active');
    });
    document.querySelector(`[data-type="${type}"]`).classList.add('active');
    
    // 更新占位符
    updatePlaceholder();
    
    // 隐藏处理按钮
    hideProcessingButton();
}

function switchToUploadMode() {
    uploadMode = !uploadMode;
    const wrapper = elements.searchInput.closest('.search-input-wrapper');
    
    if (uploadMode) {
        elements.searchInput.placeholder = '点击此处选择PDF文件';
        elements.searchInput.readOnly = true;
        elements.searchInput.classList.add('upload-mode');
        wrapper.classList.add('upload-mode');
        elements.searchInput.onclick = triggerPdfUpload;
        elements.searchBtn.querySelector('.action-icon').textContent = '📁';
        
        // 重置搜索类型选择
        document.querySelectorAll('.function-option').forEach(option => {
            option.classList.remove('active');
        });
    } else {
        elements.searchInput.readOnly = false;
        elements.searchInput.classList.remove('upload-mode');
        wrapper.classList.remove('upload-mode');
        elements.searchInput.onclick = null;
        elements.searchBtn.querySelector('.action-icon').textContent = '→';
        updatePlaceholder();
        
        // 恢复搜索类型选择
        document.querySelector(`[data-type="${currentSearchType}"]`).classList.add('active');
    }
    
    elements.searchInput.value = '';
    closeFunctionMenu();
}

function updatePlaceholder() {
    elements.searchInput.placeholder = '请描述您的学习需求，AI教伴将帮您智能搜索';
}

// 显示处理按钮
function showProcessingButton(filename, title) {
    const uploadSuccessActions = document.getElementById('uploadSuccessActions');
    const successFilename = document.getElementById('successFilename');
    const startProcessingBtn = document.getElementById('startProcessingBtn');
    
    if (uploadSuccessActions && successFilename && startProcessingBtn) {
        // 设置文件名
        successFilename.textContent = title;
        
        // 绑定处理按钮点击事件
        startProcessingBtn.onclick = function() {
            startProcessingFromCenter(filename, title);
        };
        
        // 显示容器
        uploadSuccessActions.classList.remove('hidden');
        
        // 隐藏其他面板
        hideAnalysisAndResults();
    }
}

// 从中央按钮开始处理，像后端发送背景和音色
// 接入处理md
// 【替换为以下完整函数】
async function startProcessingFromCenter(filename, title) {
    const startProcessingBtn = document.getElementById('startProcessingBtn');
    
    if (!startProcessingBtn) return;
    
    try {
        const originalText = startProcessingBtn.innerHTML;
        startProcessingBtn.innerHTML = '<span class="button-icon">⏳</span>启动中...';
        startProcessingBtn.disabled = true;

        // 1. 创建一个 FormData 对象
        const formData = new FormData();
        
        // 2. 将所有需要的数据作为键值对追加进去
        formData.append('filename', filename);
        formData.append('title', title); // 虽然后端没用，但可以传
        formData.append('output_format', document.getElementById('outputFormatSelect').value);
        
        // 从全局设置中获取视频专属配置
        const settings = videoAdvancedSettings;
        formData.append('video_duration', settings.duration);
        formData.append('voice_type', settings.voice);

        // 如果是自定义音色，则追加文件和文本
        if (settings.voice === 'custom') {
            if (settings.voiceFile) {
                // key 必须和后端 request.files.get('voiceFile') 一致
                formData.append('voiceFile', settings.voiceFile); 
            }
            if (settings.voiceText) {
                // key 必须和后端 request.form.get('voiceText') 一致
                formData.append('voiceText', settings.voiceText); 
            }

        }

        // 【新增】处理背景图片
        // key 必须和后端 request.form.get('background_choice') 一致
        formData.append('background_choice', settings.background); 
        
        if (settings.background === 'custom' && settings.backgroundFile) {
            // key 必须和后端 request.files.get('backgroundFile') 一致
            formData.append('backgroundFile', settings.backgroundFile);
        }

        // 【增加这行调试代码】
        // FormData 无法直接打印，需要遍历它的条目
        console.log("即将发送的FormData内容:");
        for (let [key, value] of formData.entries()) {
            console.log(`  ${key}:`, value);
        }

        // 3. 发送 fetch 请求
        //    注意：当使用 FormData 时，不需要手动设置 'Content-Type' header，
        //    浏览器会自动设置为 'multipart/form-data' 并包含正确的 boundary。
        const response = await fetch('/start-processing', {
            method: 'POST',
            body: formData // 直接将 formData 对象作为 body
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`开始处理论文: ${title}`);
            
            currentProcessing = {
                processId: data.process_id,
                filename: filename,
                title: title,
                button: startProcessingBtn,
                output_format: document.getElementById('outputFormatSelect').value
            };
            
            // 隐藏上传成功的操作区域
            const uploadSuccessActions = document.getElementById('uploadSuccessActions');
            if (uploadSuccessActions) {
                uploadSuccessActions.classList.add('hidden');
            }
            
            // 显示处理状态卡片，此时才会显示进度条和步骤可视化
            showProcessingInSameCard(data.process_id, title);
            startStatusPolling(data.process_id);
            
        } else {
            showError(data.error || '启动处理失败');
            startProcessingBtn.innerHTML = originalText;
            startProcessingBtn.disabled = false;
        }
        
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Processing start error:', error);
        startProcessingBtn.innerHTML = '<span class="button-icon">🚀</span>开始处理';
        startProcessingBtn.disabled = false;
    }
}

// 隐藏处理按钮
function hideProcessingButton() {
    const uploadSuccessActions = document.getElementById('uploadSuccessActions');
    if (uploadSuccessActions) {
        uploadSuccessActions.classList.add('hidden');
    }
}

// 隐藏分析和结果面板
function hideAnalysisAndResults() {
    const analysisCard = document.getElementById('analysisCard');
    const resultsCard = document.getElementById('resultsCard');
    
    if (analysisCard) analysisCard.classList.add('hidden');
    if (resultsCard) resultsCard.classList.add('hidden');
}

function triggerPdfUpload() {
    if (uploadMode) {
        elements.pdfFileInput.click();
    }
}

async function handlePdfUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    showLoading('正在上传PDF文件');

    try {
        const formData = new FormData();
        formData.append('pdf_file', file);

        const response = await fetch('/upload-pdf', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showSuccess(`成功上传PDF文件: ${file.name}`);
            loadContentList();
            switchToUploadMode(); // 切换回搜索模式
            
            // 显示处理按钮
            showProcessingButton(data.filename, data.title || file.name);
        } else {
            showError(data.error || '上传失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Upload error:', error);
    } finally {
        hideLoading();
        event.target.value = '';
    }
}

async function handleSearch() {
    if (uploadMode) {
        triggerPdfUpload();
        return;
    }

    const userInput = elements.searchInput.value.trim();
    if (!userInput) {
        elements.searchInput.focus();
        return;
    }

    originalUserInput = userInput;
    clearAllTimers();
    
    showLoading('正在分析您的需求');
    hideResults();

    try {
        const response = await fetch('/analyze-need', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_input: userInput,
                search_type: currentSearchType
            })
        });

        const data = await response.json();

        if (data.success) {
            analysisResult = data;
            showAnalysisResult(data);
        } else {
            showError(data.error || '需求分析失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Analysis error:', error);
    } finally {
        hideLoading();
    }
}

function showAnalysisResult(data) {
    document.getElementById('extractedKeyword').textContent = data.keyword;
    document.getElementById('analysisReasoning').textContent = data.reasoning;
    document.getElementById('searchIntent').textContent = data.search_intent;
    
    elements.analysisCard.classList.remove('hidden');
    startAutoConfirmTimer();
}

async function confirmAndSearch() {
    if (!analysisResult) return;

    clearAllTimers();
    showLoading('正在搜索相关内容');
    hideAnalysis();

    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                search_type: currentSearchType,
                keyword: analysisResult.keyword
            })
        });

        const data = await response.json();

        if (data.success) {
            currentKeyword = analysisResult.keyword;
            currentSearchResults = data.results;
            showSearchResults(data);
        } else {
            showError(data.error || '搜索失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Search error:', error);
    } finally {
        hideLoading();
    }
}

function modifyKeyword() {
    clearAllTimers();
    
    const newKeyword = prompt('请输入修改后的关键词：', analysisResult.keyword);
    if (newKeyword && newKeyword.trim()) {
        analysisResult.keyword = newKeyword.trim();
        document.getElementById('extractedKeyword').textContent = newKeyword.trim();
    }
    
    startAutoConfirmTimer();
}

function cancelAnalysis() {
    clearAllTimers();
    hideAnalysis();
    elements.searchInput.value = '';
    elements.searchInput.focus();
    analysisResult = null;
}

function showSearchResults(data) {
    const { search_type, keyword, results } = data;
    
    // 更新标题和元信息
    document.getElementById('resultsTitle').textContent = `${search_type === 'web' ? '网页' : '论文'}搜索结果`;
    document.getElementById('resultsMeta').textContent = `关键词: "${keyword}" · 共找到 ${results.total_count} 条结果`;
    
    // 生成结果列表
    const container = document.getElementById('resultsContainer');
    if (results.items.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📄</div>
                <div>未找到相关结果，请尝试使用其他关键词</div>
            </div>
        `;
    } else {
        container.innerHTML = results.items.map((item, index) => `
            <div class="result-item">
                <input type="checkbox" class="result-checkbox" data-url="${item.url}" data-index="${index}">
                <div class="result-content">
                    <div class="result-title" onclick="window.open('${item.url}', '_blank')">${item.title}</div>
                    <div class="result-url">${item.url}</div>
                    <div class="result-description">${search_type === 'web' ? item.content : item.abstract}</div>
                </div>
            </div>
        `).join('');
        
        // 设置事件监听
        setupCheckboxListeners();
        document.getElementById('controlsBar').style.display = 'flex';
    }
    
    elements.resultsCard.classList.remove('hidden');
    startAutoFilterTimer();
}

function setupCheckboxListeners() {
    document.querySelectorAll('.result-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            clearTimer('autoFilter');
            updateSelectedCount();
        });
    });
}

function updateSelectedCount() {
    const count = document.querySelectorAll('.result-checkbox:checked').length;
    document.getElementById('selectedCount').textContent = count;
    document.getElementById('crawlBtn').disabled = count === 0;
}

// ===== 智能筛选功能 =====
async function performSmartFilter() {
    if (!currentSearchResults || !originalUserInput) {
        showError('没有可用的搜索结果进行智能筛选');
        return;
    }

    clearTimer('autoFilter');
    
    const btn = document.getElementById('smartFilterBtn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '正在智能筛选...';

    try {
        const response = await fetch('/smart-filter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                original_input: originalUserInput,
                keyword: currentKeyword,
                papers: currentSearchResults.items,
                search_type: currentSearchType
            })
        });

        const data = await response.json();

        if (data.success) {
            showFilterResult(data);
        } else {
            showError(data.error || '智能筛选失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Smart filter error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function showFilterResult(data) {
    // 清除现有选择
    document.querySelectorAll('.result-checkbox').forEach(cb => cb.checked = false);
    
    // 根据AI推荐选择项目
    data.recommended_papers.forEach(item => {
        const checkbox = document.querySelector(`[data-index="${item.original_index}"]`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });
    
    updateSelectedCount();
    
    // 显示筛选结果
    document.getElementById('filterReasoning').textContent = data.reasoning;
    document.getElementById('filterResult').classList.remove('hidden');
    
    startAutoCrawlTimer();
}

function confirmFilter() {
    clearTimer('autoCrawl');
    document.getElementById('filterResult').classList.add('hidden');
    crawlSelected();
}

function cancelFilter() {
    clearTimer('autoCrawl');
    document.querySelectorAll('.result-checkbox').forEach(cb => cb.checked = false);
    updateSelectedCount();
    document.getElementById('filterResult').classList.add('hidden');
}

// ===== 学习资料收集功能 =====
async function crawlSelected() {
    const selectedCheckboxes = document.querySelectorAll('.result-checkbox:checked');
    
    if (selectedCheckboxes.length === 0) {
        showError('请先选择要收集的学习资料');
        return;
    }

    clearAllTimers();

    const urls = Array.from(selectedCheckboxes).map(cb => cb.dataset.url);
    const titles = Array.from(selectedCheckboxes).map(cb => {
        const item = cb.closest('.result-item');
        const title = item.querySelector('.result-title').textContent;
        return title.trim();
    });

    const btn = document.getElementById('crawlBtn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '正在收集...';

    try {
        const endpoint = currentSearchType === 'paper' ? '/crawl' : '/crawl-webpages';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls, titles })
        });

        const data = await response.json();

        if (data.success) {
            const type = currentSearchType === 'paper' ? '论文' : '网页';
            showSuccess(`成功收集 ${data.crawled_count} 个${type}到学习资料库！`);
            loadContentList();
        } else {
            showError(data.error || '收集失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Crawl error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ===== 内容管理功能 =====
async function loadContentList() {
    try {
        const [pdfResponse, webResponse] = await Promise.all([
            fetch('/pdf-list'),
            fetch('/webpage-list')
        ]);
        
        const pdfData = await pdfResponse.json();
        const webData = await webResponse.json();
        
        const pdfs = pdfData.success ? pdfData.pdfs : [];
        const webpages = webData.success ? webData.webpages : [];
        
        displayContentList(pdfs, webpages);
    } catch (error) {
        console.error('获取内容列表失败:', error);
        displayEmptyContentList();
    }
}

function displayContentList(pdfs, webpages) {
    const container = document.getElementById('contentSections');
    let html = '';

    if (pdfs.length === 0 && webpages.length === 0) {
        html = `
            <div class="empty-state">
                <div class="empty-icon">📁</div>
                <div>暂无已保存的内容</div>
            </div>
        `;
    } else {
        if (pdfs.length > 0) {
            // html += `
            //     <div class="content-section">
            //         <div class="section-title">论文 (${pdfs.length})</div>
            //         ${pdfs.map(pdf => `
            //             <div class="content-item">
            //                 <div class="content-title">${pdf.title}</div>
            //                 <div class="content-actions">
            //                     <button class="preview-btn" onclick="previewContent('${pdf.filename}', 'pdf')">预览</button>
            //                     <button class="delete-btn" onclick="deleteContent('${pdf.filename}', 'pdf')" title="删除">🗑️</button>
            //                 </div>
            //             </div>
            //         `).join('')}
            //     </div>
            // `;
            html += `
                <div class="content-section">
                    <div class="section-title">论文 (${pdfs.length})</div>
                    ${pdfs.map(item => {
                        // 【核心智能判断】
                        if (item.type === 'folder') {
                            // 如果是文件夹，渲染成可折叠的分组
                            return `
                                <div class="sidebar-group" data-batch-id="${item.batch_id}">
                                    <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                                        <div class="content-title">
                                            <span class="toggle-icon">▼</span>
                                            <span>📁</span>
                                            <span title="${item.name}">${item.name} (${item.file_count})</span>
                                        </div>
                                        <div class="content-actions">
                                            <button class="delete-btn" onclick="deleteFolder('${item.batch_id}', event)" title="删除整个文件夹">🗑️</button>
                                        </div>
                                    </div>
                                    <div class="sidebar-group-content">
                                        ${item.files.map(fileInfo => `
                                            <div class="content-item">
                                                <div class="content-title" title="${fileInfo.original_name}">${fileInfo.original_name}</div>
                                                <div class="content-actions">
                                                    <button class="preview-btn" onclick="previewContent('${fileInfo.saved_name}', 'pdf')">预览</button>
                                                    <button class="delete-btn" onclick="deleteContent('${fileInfo.saved_name}', 'pdf')" title="删除">🗑️</button>
                                                </div>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            `;
                        } else {
                            // 如果是单篇文件，渲染成普通的卡片
                            return `
                                <div class="content-item">
                                    <div class="content-title">${item.title}</div>
                                    <div class="content-actions">
                                        <button class="preview-btn" onclick="previewContent('${item.filename}', 'pdf')">预览</button>
                                        <button class="delete-btn" onclick="deleteContent('${item.filename}', 'pdf')" title="删除">🗑️</button>
                                    </div>
                                </div>
                            `;
                        }
                    }).join('')}
                </div>
            `;
        }




        if (webpages.length > 0) {
            html += `
                <div class="content-section">
                    <div class="section-title">网页 (${webpages.length})</div>
                    ${webpages.map(webpage => `
                        <div class="content-item">
                            <div class="content-title">${webpage.title}</div>
                            <div class="content-actions">
                                <button class="preview-btn" onclick="previewContent('${webpage.filename}', 'webpage')">预览</button>
                                <button class="delete-btn" onclick="deleteContent('${webpage.filename}', 'webpage')" title="删除">🗑️</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    }

    container.innerHTML = html;
}

function displayEmptyContentList() {
    document.getElementById('contentSections').innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">📁</div>
            <div>暂无已保存的内容</div>
        </div>
    `;
}

// function previewContent(filename, type) {
//     const modal = elements.previewModal;
//     const title = document.getElementById('modalTitle');
//     const iframe = document.getElementById('previewIframe');
    
//     title.textContent = `${type === 'pdf' ? 'PDF' : '网页'}预览 - ${filename}`;
//     iframe.src = `/${type === 'pdf' ? 'pdf' : 'webpage'}-preview/${encodeURIComponent(filename)}`;
//     modal.classList.remove('hidden');
    
//     document.body.style.overflow = 'hidden';
// }

function previewContent(filename, type) {
    const modal = document.getElementById('previewModal'); // 假设您有elements对象，或直接获取
    const title = document.getElementById('modalTitle');
    const iframe = document.getElementById('previewIframe');
    
    let previewUrl = '';
    // 根据类型构建正确的预览URL
    if (type === 'pdf') {
        // 我们的新后端路由是 /uploads/<filepath>
        previewUrl = `/uploads/${encodeURIComponent(filename)}`;
    } else if (type === 'webpage') {
        previewUrl = `/webpage-preview/${encodeURIComponent(filename)}`; // 网页逻辑保持不变
    }

    title.textContent = `内容预览 - ${filename}`;
    iframe.src = previewUrl;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closePreview() {
    const modal = elements.previewModal;
    const iframe = document.getElementById('previewIframe');
    
    modal.classList.add('hidden');
    iframe.src = '';
    document.body.style.overflow = 'auto';
}

async function deleteContent(filename, type) {
    if (!confirm(`确定要删除这个${type === 'pdf' ? 'PDF' : '网页'}文件吗？`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filename,
                type: type
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`成功删除${type === 'pdf' ? 'PDF' : '网页'}文件`);
            loadContentList();
        } else {
            showError(data.error || '删除失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Delete error:', error);
    }
}


// ===== 界面控制功能 =====
function toggleSidebar() {
    sidebarVisible = !sidebarVisible;
    elements.sidebar.classList.toggle('sidebar-open', sidebarVisible);
    elements.sidebarOverlay.classList.toggle('sidebar-open', sidebarVisible);
    
    // 使用箭头符号：收起时显示左箭头，展开时显示右箭头
    elements.sidebarToggle.textContent = sidebarVisible ? '›' : '‹';
    elements.sidebarToggle.title = sidebarVisible ? '隐藏内容列表' : '显示内容列表';
}

function initializeSidebar() {
    // 默认状态下侧栏是收起的
    sidebarVisible = false;
    elements.sidebar.classList.remove('sidebar-open');
    elements.sidebarOverlay.classList.remove('sidebar-open');
    elements.sidebarToggle.textContent = '‹';
    
    // 在移动设备上确保侧栏是收起的
    if (window.innerWidth <= 768) {
        sidebarVisible = false;
        elements.sidebar.classList.remove('sidebar-open');
        elements.sidebarOverlay.classList.remove('sidebar-open');
        elements.sidebarToggle.textContent = '‹';
    }
}

function handleResize() {
    if (window.innerWidth <= 768 && sidebarVisible) {
        toggleSidebar();
    }
}

async function exitApplication() {
    if (!confirm('确定要清空所有已保存的内容吗？此操作不可撤销。')) {
        return;
    }

    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '...';

    try {
        const response = await fetch('/clear-papers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            showSuccess(`成功清空了 ${data.deleted_count} 个文件`);
            displayEmptyContentList();
            hideResults();
            hideAnalysis();
            elements.searchInput.value = '';
        } else {
            showError(data.error || '清空失败');
        }
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Clear error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}












// ===== 计时器管理 =====
function startAutoConfirmTimer() {
    clearTimer('autoConfirm');
    
    const btn = document.getElementById('confirmSearchBtn');
    const originalText = btn.textContent;
    let timeLeft = 30;
    
    const updateCountdown = () => {
        btn.textContent = `${originalText} (${timeLeft}s)`;
        
        if (timeLeft <= 0) {
            clearTimer('autoConfirm');
            confirmAndSearch();
            return;
        }
        
        timeLeft--;
    };
    
    updateCountdown();
    autoConfirmTimer = setInterval(updateCountdown, 1000);
}

function startAutoFilterTimer() {
    clearTimer('autoFilter');
    
    const btn = document.getElementById('smartFilterBtn');
    const originalText = btn.textContent;
    let timeLeft = 30;
    
    const updateCountdown = () => {
        btn.textContent = `${originalText} (${timeLeft}s)`;
        
        if (timeLeft <= 0) {
            clearTimer('autoFilter');
            performSmartFilter();
            return;
        }
        
        timeLeft--;
    };
    
    updateCountdown();
    autoFilterTimer = setInterval(updateCountdown, 1000);
}

function startAutoCrawlTimer() {
    clearTimer('autoCrawl');
    
    const btn = document.getElementById('confirmFilterBtn');
    const originalText = btn.textContent;
    let timeLeft = 30;
    
    const updateCountdown = () => {
        btn.textContent = `${originalText} (${timeLeft}s)`;
        
        if (timeLeft <= 0) {
            clearTimer('autoCrawl');
            confirmFilter();
            return;
        }
        
        timeLeft--;
    };
    
    updateCountdown();
    autoCrawlTimer = setInterval(updateCountdown, 1000);
}

function clearTimer(type) {
    if (type === 'autoConfirm' && autoConfirmTimer) {
        clearInterval(autoConfirmTimer);
        autoConfirmTimer = null;
        const btn = document.getElementById('confirmSearchBtn');
        if (btn) btn.textContent = '确认搜索';
    } else if (type === 'autoFilter' && autoFilterTimer) {
        clearInterval(autoFilterTimer);
        autoFilterTimer = null;
        const btn = document.getElementById('smartFilterBtn');
        if (btn) btn.textContent = '智能筛选';
    } else if (type === 'autoCrawl' && autoCrawlTimer) {
        clearInterval(autoCrawlTimer);
        autoCrawlTimer = null;
        const btn = document.getElementById('confirmFilterBtn');
        if (btn) btn.textContent = '确认推荐';
    }
}

function clearAllTimers() {
    clearTimer('autoConfirm');
    clearTimer('autoFilter');
    clearTimer('autoCrawl');
}

// ===== 工具函数 =====
function showLoading(message = '加载中') {
    elements.loading.textContent = message;
    elements.loading.classList.remove('hidden');
    elements.searchBtn.disabled = true;
}

function hideLoading() {
    elements.loading.classList.add('hidden');
    elements.searchBtn.disabled = false;
}

function showError(message) {
    const container = document.getElementById('resultsContainer');
    container.innerHTML = `<div class="error-message">${message}</div>`;
    elements.resultsCard.classList.remove('hidden');
}

function showSuccess(message) {
    // 简单的成功提示，可以根据需要实现更复杂的通知系统
    alert(message);
}

function hideAnalysis() {
    elements.analysisCard.classList.add('hidden');
}

function hideResults() {
    elements.resultsCard.classList.add('hidden');
    const controlsBar = document.getElementById('controlsBar');
    const filterResult = document.getElementById('filterResult');
    
    if (controlsBar) controlsBar.style.display = 'none';
    if (filterResult) filterResult.classList.add('hidden');
}


// ... 此处省略大量未改变的函数 ...
// 比如 handleSearch, showAnalysisResult, crawlSelected, loadContentList 等等，都不需要改变

// ===== 【新增】视频高级设置悬浮窗功能 =====

// 根据输出格式选择，显示或隐藏"视频高级设置"按钮
// 在 js/app.js 中
function handleOutputFormatChange() {
    const format = document.getElementById('outputFormatSelect').value;
    const videoSettingsContainer = document.getElementById('videoSettingsContainer');
    
    if (format === 'video') {
        videoSettingsContainer.style.display = 'block'; // 【修改】直接控制 display 属性
    } else {
        videoSettingsContainer.style.display = 'none'; // 【修改】直接控制 display 属性
    }
}

// 打开视频设置悬浮窗
function openVideoSettingsModal() {
    document.getElementById('videoSettingsModalOverlay').classList.remove('hidden');
}

// 关闭视频设置悬浮窗
function closeVideoSettingsModal() {
    // 【新增】在关闭窗口前，检查并停止任何正在播放的音频
    if (currentPreview.audio) {
        currentPreview.audio.pause();
        currentPreview.audio.currentTime = 0;
        if (currentPreview.button) {
            currentPreview.button.innerHTML = '▶'; // 恢复按钮图标
        }
        currentPreview = { audio: null, button: null }; // 清空状态
    }
    document.getElementById('videoSettingsModalOverlay').classList.add('hidden');
}

// 在悬浮窗中选择人声
// 在 js/app.js 中

// 【替换为以下代码】
// 在 js/app.js 中
function selectVoice(element, voiceName) {
    // 视觉上：更新选中状态
    document.querySelectorAll('.voice-option-item').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');

    // 逻辑上：更新全局设置
    videoAdvancedSettings.voice = voiceName;
    videoAdvancedSettings.voiceFile = null; // 清除已上传的文件
    videoAdvancedSettings.voiceText = ''; // 清除已输入的文本

    // 【新增】隐藏文件上传信息和自定义文本输入框
    document.getElementById('voiceFileUploadInfo').innerHTML = '';
    document.getElementById('voiceTextInputContainer').classList.add('hidden');
    
    console.log('Voice selected:', videoAdvancedSettings.voice);
}

// 【新增】一个统一的、可控的音频播放函数
function playAudio(src) {
    // 如果有音频正在播放，先停止并清空它
    if (currentPlayingAudio) {
        currentPlayingAudio.pause();
        currentPlayingAudio.currentTime = 0;
        currentPlayingAudio = null;
    }

    // 创建新的音频对象
    const audio = new Audio(src);
    
    // 存储到全局变量
    currentPlayingAudio = audio;

    audio.play().catch(e => {
        console.error("音频播放失败:", e);
        showError(`无法播放音频。`);
        currentPlayingAudio = null; // 播放失败也要清空
    });

    // 播放结束后，也清空全局变量
    audio.onended = () => {
        currentPlayingAudio = null;
    };
}


// 【新增】一个统一的播放/暂停控制器函数
function playOrPausePreview(buttonElement, audioSrc) {
    // 情况一：用户点击了正在播放的那个按钮（暂停/停止）
    if (currentPreview.audio && currentPreview.button === buttonElement) {
        currentPreview.audio.pause();
        currentPreview.audio.currentTime = 0; // 直接停止并回到开头
        buttonElement.innerHTML = '▶'; // 恢复播放图标
        currentPreview = { audio: null, button: null }; // 清空状态
        return; // 操作完成，退出函数
    }

    // 情况二：有其他音频正在播放，用户点击了一个新的播放按钮
    if (currentPreview.audio) {
        currentPreview.audio.pause();
        currentPreview.audio.currentTime = 0;
        if (currentPreview.button) {
            currentPreview.button.innerHTML = '▶'; // 恢复旧按钮的图标
        }
    }

    // 情况三：开始播放新的音频
    const newAudio = new Audio(audioSrc);
    
    // 更新当前播放状态
    currentPreview = {
        audio: newAudio,
        button: buttonElement,
    };

    // 改变当前按钮的图标为暂停
    buttonElement.innerHTML = '❚❚';

    // 监听音频播放结束事件
    newAudio.onended = () => {
        if (currentPreview.button === buttonElement) {
            buttonElement.innerHTML = '▶'; // 恢复播放图标
            currentPreview = { audio: null, button: null }; // 清空状态
        }
    };
    
    // 播放音频
    newAudio.play().catch(e => {
        console.error("音频播放失败:", e);
        showError(`无法播放音频。`);
        // 如果播放失败，也要重置状态
        if (currentPreview.button === buttonElement) {
            buttonElement.innerHTML = '▶';
            currentPreview = { audio: null, button: null };
        }
    });
}


// 预览人声音频
function previewVoice(voiceFileName, event) {
    event.stopPropagation();
    const audioSrc = `/static/voices/${voiceFileName}`;
    const buttonElement = event.target; // 获取被点击的按钮元素
    playOrPausePreview(buttonElement, audioSrc); // 调用统一控制器
}

// 在 js/app.js 中

// 【替换为以下代码】
// function handleVoiceUpload(event) {
//     const file = event.target.files[0];
//     if (!file) return;

//     // 【修改】获取您指定的、位于外部的预览区域容器
//     const previewArea = document.getElementById('voiceUploadPreviewArea');
//     if (!previewArea) {
//         console.error("代码错误: 找不到 ID 为 'voiceUploadPreviewArea' 的HTML元素。");
//         showError("页面结构错误，无法显示上传预览。");
//         return;
//     }

//     const tempUrl = URL.createObjectURL(file);

//     // 【修改】动态生成预览内容，并放入外部容器中
//     previewArea.innerHTML = `
//         <div class="uploaded-item-info">
//             <span>已选择音色: <strong>${file.name}</strong></span>
//             <button class="preview-audio-btn" onclick="playOrPausePreview(this, '${tempUrl}')">▶</button>
//         </div>
//     `;

//     // 【修改】让预览区域可见
//     previewArea.classList.remove('hidden');

//     // ... 函数的其余部分（更新全局设置和选中状态）保持不变 ...
//     videoAdvancedSettings.voice = 'custom';
//     videoAdvancedSettings.voiceFile = file;
//     document.querySelectorAll('.voice-option-item').forEach(el => el.classList.remove('selected'));
//     event.target.closest('.voice-option-item.upload-item').classList.add('selected');
// }

// 【替换为以下完整函数】
function handleVoiceUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 1. 获取文件信息和文本输入框的容器
    const fileInfoContainer = document.getElementById('voiceFileUploadInfo');
    const textInputContainer = document.getElementById('voiceTextInputContainer');

    // 2. 清空之前可能存在的预览信息
    fileInfoContainer.innerHTML = ''; 

    // 3. 创建一个新的 div 作为预览信息的容器，并应用样式
    const previewWrapper = document.createElement('div');
    previewWrapper.className = 'uploaded-item-info'; // 使用我们之前定义的样式

    // 4. 创建显示文件名的 span
    const fileNameSpan = document.createElement('span');
    fileNameSpan.textContent = file.name;

    // 5. 创建播放/暂停按钮
    const playBtn = document.createElement('button');
    playBtn.className = 'preview-audio-btn';
    playBtn.innerHTML = '▶'; // 初始显示为播放图标

    // 6. 创建一个 Audio 对象，但先不播放
    const tempUrl = URL.createObjectURL(file);
    const audio = new Audio(tempUrl);
    let isPlaying = false;

    // 7. 为按钮添加点击事件，实现播放/暂停切换
    playBtn.onclick = (e) => {
        e.stopPropagation(); // 阻止事件冒泡
        if (isPlaying) {
            audio.pause();
        } else {
            audio.play().catch(err => console.error("音频播放失败:", err));
        }
    };

    // 8. 监听音频的播放和暂停事件，以更新按钮的图标
    audio.onplay = () => {
        isPlaying = true;
        playBtn.innerHTML = '❚❚'; // 暂停图标
    };
    audio.onpause = () => {
        isPlaying = false;
        playBtn.innerHTML = '▶'; // 播放图标
        audio.currentTime = 0; // 暂停后将播放头重置到开头
    };
    audio.onended = () => {
        isPlaying = false;
        playBtn.innerHTML = '▶'; // 播放结束后也恢复成播放图标
    };

    // 9. 将文件名和按钮添加到包装容器中
    previewWrapper.appendChild(fileNameSpan);
    previewWrapper.appendChild(playBtn);
    
    // 10. 将整个预览包装容器添加到页面上
    fileInfoContainer.appendChild(previewWrapper);


    // --- 以下是自定义文本输入框的逻辑，保持不变 ---

    // 动态创建文本输入框并显示它
    textInputContainer.innerHTML = `
        <textarea id="customVoiceText" class="custom-voice-textarea" placeholder="请以文字形式输入音频，这段文字将用于AI生成语音。"></textarea>
    `;
    textInputContainer.classList.remove('hidden');

    // 为文本框绑定 input 事件，实时更新全局设置
    const customVoiceTextArea = document.getElementById('customVoiceText');
    if(customVoiceTextArea) {
        customVoiceTextArea.addEventListener('input', (e) => {
            videoAdvancedSettings.voiceText = e.target.value;
        });
    }

    // 更新全局设置
    videoAdvancedSettings.voice = 'custom';
    videoAdvancedSettings.voiceFile = file;
    videoAdvancedSettings.voiceText = ''; 

    // 视觉上选中"上传音色"选项
    document.querySelectorAll('.voice-option-item').forEach(el => el.classList.remove('selected'));
    event.target.closest('.voice-option-item.upload-item').classList.add('selected');
}
// 【新增】一个用于播放上传音频的函数
function previewUploadedAudio(url) {
    const audio = new Audio(url);
    audio.play().catch(e => console.error("上传音频播放失败:", e));
    // 当预览结束后，释放内存
    audio.onended = () => {
    URL.revokeObjectURL(url);
    };
}


// 在悬浮窗中选择背景
// 在 js/app.js 中

// 【替换为以下代码】
function selectBackground(element, backgroundName) {
    // 视觉上：移除所有选项的 'selected'，再给当前点击的添加上
    document.querySelectorAll('.background-option-item').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');

    // 逻辑上：更新全局设置
    if (backgroundName === 'custom') {
        // 如果点击的是上传的图片，我们什么都不用做，因为 handleBackgroundUpload 已经把 file 对象存好了
        videoAdvancedSettings.background = 'custom';
    } else {
        // 如果点击的是预设的图片，就用它的名字更新设置，并清空之前可能上传的文件
        videoAdvancedSettings.background = backgroundName;
        videoAdvancedSettings.backgroundFile = null;
    }
    
    console.log('背景已选择:', videoAdvancedSettings.background, videoAdvancedSettings.backgroundFile?.name || '');
}

// 处理背景图片上传（逻辑与 handleVoiceUpload 类似）
// 在 js/app.js 中

// 【替换为以下代码】
function handleSettingsBackgroundUpload(event) {
    const file = event.target.files[0];
    if (!file || !file.type.startsWith('image/')) {
        showError("请选择一个图片文件。");
        return;
    }

    // 1. 获取图片画廊和已存在的用户上传预览块
    const gallery = document.querySelector('.background-gallery');
    let userUploadPreview = document.getElementById('userUploadedBackground');

    // 2. 如果这个预览块不存在，就创建一个新的
    if (!userUploadPreview) {
        userUploadPreview = document.createElement('div');
        userUploadPreview.id = 'userUploadedBackground';
        userUploadPreview.className = 'background-option-item';
        // 将它插入到"上传"按钮的前面
        gallery.insertBefore(userUploadPreview, gallery.querySelector('.upload-item'));
    }

    // 3. 为上传的图片创建临时URL
    const tempUrl = URL.createObjectURL(file);

    // 4. 更新预览块的内容和点击事件
    userUploadPreview.innerHTML = `<img src="${tempUrl}" alt="用户上传的背景预览">`;
    // 点击这个块时，同样调用 selectBackground，并传入自己作为元素
    userUploadPreview.onclick = () => selectBackground(userUploadPreview, 'custom');

    // 5. 更新全局设置
    videoAdvancedSettings.background = 'custom';
    videoAdvancedSettings.backgroundFile = file;

    // 6. 自动选中刚刚上传的这张图片
    selectBackground(userUploadPreview, 'custom');
}

// 保存视频设置
function saveVideoSettings() {
    // 从模态框内的元素读取最终设置
    videoAdvancedSettings.duration = document.getElementById('modalVideoDurationSelect').value;
    
    // 其他设置（如voice, background）在点击时已经更新了，这里无需再次读取
    
    showSuccess('视频设置已保存！');
    closeVideoSettingsModal();
}




// ===== 全局暴露的函数（用于HTML中的onclick事件） =====
// 这些函数需要在全局作用域中可访问
window.switchToUploadMode = switchToUploadMode;
window.triggerPdfUpload = triggerPdfUpload;
window.handlePdfUpload = handlePdfUpload;
window.performSmartFilter = performSmartFilter;
window.crawlSelected = crawlSelected;
window.previewContent = previewContent;
window.closePreview = closePreview;
window.toggleSidebar = toggleSidebar;
window.exitApplication = exitApplication;
window.toggleFunctionMenu = toggleFunctionMenu;
window.openFunctionMenu = openFunctionMenu;
window.closeFunctionMenu = closeFunctionMenu; 


// ... 其他暴露的函数 ...
// 【新增】暴露新函数
window.handleOutputFormatChange = handleOutputFormatChange;
window.openVideoSettingsModal = openVideoSettingsModal;
window.closeVideoSettingsModal = closeVideoSettingsModal;
window.selectVoice = selectVoice;
window.previewVoice = previewVoice;
window.handleVoiceUpload = handleVoiceUpload;
window.selectBackground = selectBackground;
window.handleSettingsBackgroundUpload = handleSettingsBackgroundUpload; // 【新增】
window.saveVideoSettings = saveVideoSettings;
window.previewUploadedAudio = previewUploadedAudio;//播放上传音频的函数，暴露到全局
// 在 js/app.js 文件末尾
window.playAudio = playAudio; // 【新增】
// ... 文件余下部分保持不变 ...
window.playOrPausePreview = playOrPausePreview;

// ===== 论文处理功能 =====

// 当前处理任务
let currentProcessing = null;
let processingInterval = null;

async function startProcessing(filename, title) {
    try {
        const button = event.target;
        const originalText = button.textContent;
        
        // 更新按钮状态
        button.textContent = '启动中...';
        button.disabled = true;
        
        // 获取之前的输出格式，如果是重试的话
        const previousOutputFormat = (currentProcessing && currentProcessing.output_format) ? currentProcessing.output_format : 'video';
        
        const response = await fetch('/start-processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filename,
                video_duration: 'medium',  // 默认中等时长
                voice_type: 'female',      // 默认女声
                output_format: previousOutputFormat // 使用之前的输出格式
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`开始处理论文: ${title}`);
            
            // 保存当前处理信息
            currentProcessing = {
                processId: data.process_id,
                filename: filename,
                title: title,
                button: button,
                output_format: previousOutputFormat // 保存输出格式信息
            };
            
            // 显示处理进度界面
            showProcessingProgress(data.process_id, title);
            
            // 开始状态轮询
            startStatusPolling(data.process_id);
            
        } else {
            showError(data.error || '启动处理失败');
            button.textContent = originalText;
            button.disabled = false;
        }
        
    } catch (error) {
        showError('网络错误，请稍后重试');
        console.error('Processing start error:', error);
        button.textContent = '开始处理';
        button.disabled = false;
    }
}

// 全局变量来跟踪处理开始时间
let processingStartTime = null;
let stepStartTimes = {}; // 记录每个步骤的开始时间
let stepDurations = {}; // 记录每个步骤的持续时间
let timeUpdateInterval = null; // 时间更新的定时器

function showProcessingProgress(processId, title) {
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
    
    // 获取当前选择的输出格式
    const outputFormat = document.getElementById('outputFormatSelect').value;
    
    // 更新活动处理任务显示
    const activeProcessing = document.getElementById('activeProcessing');
    if (activeProcessing) {
        activeProcessing.innerHTML = `
            <div class="current-task">
                <!-- 任务标题、ID和时间信息已移除 -->
                
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    </div>
                </div>
                
                <!-- 取消按钮已移动到HTML中的该步骤进度卡片 -->
            </div>
        `;
    }
    
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
    
    // 修改步骤卡片，根据输出格式显示不同的步骤
    const stepsContainer = document.querySelector('.steps-container');
    if (stepsContainer) {
        if (outputFormat === 'markdown') {
            // Markdown格式只显示三个步骤
            stepsContainer.innerHTML = `
                <div class="step-item" data-step="1">
                    <div class="step-icon">📄</div>
                    <div class="step-text">论文解析者</div>
                </div>
                <div class="step-item" data-step="2">
                    <div class="step-icon">📝</div>
                    <div class="step-text">内容生成员</div>
                </div>
                <div class="step-item" data-step="3">
                    <div class="step-icon">🎦</div>
                    <div class="step-text">最终合并者</div>
                </div>
            `;
        } else {
            // 视频格式显示原有的9个步骤
            stepsContainer.innerHTML = `
                <div class="step-item" data-step="1">
                    <div class="step-icon">📄</div>
                    <div class="step-text">论文解析者</div>
                </div>
                <div class="step-item" data-step="2">
                    <div class="step-icon">🎬</div>
                    <div class="step-text">内容生成员</div>
                </div>
                <div class="step-item" data-step="3">
                    <div class="step-icon">📝</div>
                    <div class="step-text">交互编辑者</div>
                </div>
                <div class="step-item" data-step="4">
                    <div class="step-icon">🎥</div>
                    <div class="step-text">视频预览员</div>
                </div>
                <div class="step-item" data-step="5">
                    <div class="step-icon">💬</div>
                    <div class="step-text">反馈编辑者</div>
                </div>
                <div class="step-item" data-step="6">
                    <div class="step-icon">🎵</div>
                    <div class="step-text">语音合成员</div>
                </div>
                <div class="step-item" data-step="7">
                    <div class="step-icon">🔄</div>
                    <div class="step-text">音视频对齐者</div>
                </div>
                <div class="step-item" data-step="8">
                    <div class="step-icon">🎬</div>
                    <div class="step-text">视频渲染员</div>
                </div>
                <div class="step-item" data-step="9">
                    <div class="step-icon">🎦</div>
                    <div class="step-text">最终合并者</div>
                </div>
            `;
        }
    }
    
    // 滚动到状态卡片
    processingStatusCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // 重置时间估算数据和启动时间更新
    resetTimeEstimation();
    startTimeUpdateTimer();
}

// 清理日志容器的辅助函数
function clearLogContainer() {
    const existingLogContainers = document.querySelectorAll('.log-container');
    existingLogContainers.forEach(container => {
        // 只清理动态创建的日志容器，不是在 activeProcessing 内的
        if (!container.closest('#activeProcessing')) {
            container.remove();
        }
    });
}

function hideProcessingProgress() {
    const statusCard = document.getElementById('processingStatusCard');
    if (statusCard) {
        statusCard.classList.add('hidden');
    }
    
    // 清理日志容器
    clearLogContainer();
    
    // 重置时间跟踪变量
    processingStartTime = null;
    stepStartTimes = {};
    stepDurations = {};
}

function minimizeProcessingStatus() {
    const statusContent = document.getElementById('processingStatusContent');
    const minimizeBtn = document.querySelector('.minimize-btn');
    
    if (statusContent.style.display === 'none') {
        statusContent.style.display = 'block';
        minimizeBtn.textContent = '-';
        minimizeBtn.title = '最小化';
    } else {
        statusContent.style.display = 'none';
        minimizeBtn.textContent = '+';
        minimizeBtn.title = '展开';
    }
}

function toggleLogDisplay() {
    const logContent = document.getElementById('logContent');
    const logToggle = document.getElementById('logToggle');
    
    if (logContent.style.display === 'none') {
        logContent.style.display = 'block';
        logToggle.textContent = '▼';
    } else {
        logContent.style.display = 'none';
        logToggle.textContent = '▶';
    }
}

function startStatusPolling(processId) {
    // 清除之前的轮询
    if (processingInterval) {
        clearInterval(processingInterval);
    }
    
    // 开始新的轮询
    processingInterval = setInterval(async () => {
        try {
            console.log(`轮询处理状态: ${processId}`);
            const response = await fetch(`/processing-status/${processId}`);
            const data = await response.json();
            
            console.log('API响应数据:', data);
            
            if (data.success && !data.error) {
                updateProcessingProgress(data);
                
                // 如果处理完成或失败，停止轮询
                if (data.status === 'completed' || data.status === 'failed') {
                    console.log('处理完成，停止轮询');
                    clearInterval(processingInterval);
                    processingInterval = null;
                    // 同时清除时间更新定时器
                    if (timeUpdateInterval) {
                        clearInterval(timeUpdateInterval);
                        timeUpdateInterval = null;
                    }
                    onProcessingComplete(data);
                }
            } else {
                console.error('获取处理状态失败:', data.error || '未知错误');
                if (data.error) {
                    // 如果任务不存在，停止轮询
                    if (data.error.includes('不存在')) {
                        clearInterval(processingInterval);
                        processingInterval = null;
                        // 同时清除时间更新定时器
                        if (timeUpdateInterval) {
                            clearInterval(timeUpdateInterval);
                            timeUpdateInterval = null;
                        }
                    }
                }
            }
        } catch (error) {
            console.error('状态轮询错误:', error);
        }
    }, 1000); // 每1秒轮询一次，提高实时性
}

function updateProcessingProgress(statusData) {
    const progressFill = document.getElementById('progressFill');
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const logContent = document.getElementById('logContent');
    
    // 缓存状态数据供时间更新定时器使用
    window.lastStatusData = statusData;
    
    // 更新主进度条
    if (progressFill) {
        progressFill.style.width = `${statusData.progress}%`;
    }
    
    // 更新总体进度条（在步骤区域）
    if (progressBar) {
        progressBar.style.width = `${statusData.progress}%`;
    }
    
    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(statusData.progress)}%`;
    }
    
    // 更新步骤可视化
    updateStepsVisualization(statusData);
    
    // 更新时间估计
    updateTimeEstimate(statusData);
    
    // 检查是否进入等待编辑状态
    if (statusData.status === 'waiting_for_edit' && statusData.stage === 'waiting_for_edit') {
        // 停止轮询，显示编辑界面
        clearInterval(processingInterval);
        processingInterval = null;
        // 同时清除时间更新定时器
        if (timeUpdateInterval) {
            clearInterval(timeUpdateInterval);
            timeUpdateInterval = null;
        }
        showEditingInterface(statusData);
        return;
    }
    
    // 检查是否进入等待反馈编辑状态
    if (statusData.status === 'waiting_feedback') {
        // 停止轮询，显示反馈编辑界面
        clearInterval(processingInterval);
        processingInterval = null;
        // 同时清除时间更新定时器
        if (timeUpdateInterval) {
            clearInterval(timeUpdateInterval);
            timeUpdateInterval = null;
        }
        showFeedbackEditingInterface(statusData);
        return;
    }
    
    // 更新日志
    if (logContent && statusData.recent_logs) {
        console.log('更新日志，日志数量:', statusData.recent_logs.length);
        const newLogs = statusData.recent_logs.slice(-50); // 显示最近50条
        
        logContent.innerHTML = newLogs.map((log, index) => {
            // 确保消息内容存在且不为空
            const message = log.message || '';
            if (!message.trim()) return '';
            
            // 过滤掉特定的步骤信息日志
            if (message.includes('Step 1-3') || 
                message.includes('Step 3.5') || 
                message.includes('Step 4.5') || 
                message.includes('预览视频渲染')) {
                return '';
            }
            
            let extraClass = '';
            // 添加特殊样式用于重要提示
            if (message.includes('⏳ 注意') || message.includes('🎵 注意')) {
                extraClass = ' important-notice';
            } else if (message.includes('⚠️ 警告')) {
                extraClass = ' warning-notice';
            } else if (message.includes('[PROG]') && message.includes('批量')) {
                extraClass = ' progress-info';
            } else if (message.includes('💓 [心跳]')) {
                extraClass = ' heartbeat-message';
            } else if (message.includes('🤖 正在调用AI API')) {
                extraClass = ' ai-api-notice';
            } else if (message.includes('[STEP')) {
                extraClass = ' step-message';
            } else if (message.includes('[CMD]') || message.includes('$ ')) {
                extraClass = ' command-message';
            }
            
            return `<div class="log-item${extraClass}" data-index="${index}">
                <span class="log-message">${escapeHtml(message)}</span>
            </div>`;
        }).filter(item => item !== '').join('');
        
        // 滚动到底部
        logContent.scrollTop = logContent.scrollHeight;
        console.log('日志更新完成');
        
        // 检查是否有长时间运行的提示，如果有则添加额外的UI提示
        const hasLongRunningNotice = newLogs.some(log => 
            log.message && (log.message.includes('⏳ 注意') || log.message.includes('🎵 注意'))
        );
        
        if (hasLongRunningNotice) {
            addLongRunningIndicator();
        }
    } else {
        console.log('日志容器或日志数据不存在');
    }
}

function addLongRunningIndicator() {
    // 如果还没有长时间运行指示器，则添加一个
    if (!document.getElementById('longRunningIndicator')) {
        const indicator = document.createElement('div');
        indicator.id = 'longRunningIndicator';
        indicator.className = 'long-running-indicator';
        indicator.innerHTML = `
            <div class="indicator-content">
                <div class="spinner"></div>
                <div class="indicator-text">
                    <strong>正在执行耗时操作</strong><br>
                    系统正在处理，请耐心等待...
                </div>
            </div>
        `;
        
        const statusCard = document.querySelector('.processing-status-card');
        if (statusCard) {
            statusCard.appendChild(indicator);
        }
    }
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 动态时间估算系统
let timeEstimationData = {
    stepHistory: [],
    averageStepTimes: {},
    learningRate: 0.3
};

function updateTimeEstimate(statusData) {
    const elapsedTimeElement = document.getElementById('elapsedTime');
    const estimatedTimeElement = document.getElementById('estimatedTime');
    const completionTimeElement = document.getElementById('completionTime');
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    
    if (!processingStartTime) {
        return;
    }
    
    const now = new Date();
    const elapsedMs = now - processingStartTime;
    const progress = statusData.progress || 0;
    
    // 更新进度条
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        
        // 根据状态更新进度条样式
        progressBar.classList.remove('completed', 'failed');
        if (statusData.status === 'completed') {
            progressBar.classList.add('completed');
        } else if (statusData.status === 'failed') {
            progressBar.classList.add('failed');
        }
    }
    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(progress)}%`;
    }
    
    // 更新已用时间
    if (elapsedTimeElement) {
        elapsedTimeElement.textContent = formatDuration(elapsedMs);
        elapsedTimeElement.className = 'time-value elapsed';
    }
    
    // 智能时间估算
    const currentStepNumber = getCurrentStepNumber(statusData.current_step);
    updateStepHistory(currentStepNumber, elapsedMs);
    
    if (progress > 0 && progress < 100) {
        const estimatedRemainingMs = calculateSmartEstimate(progress, currentStepNumber, elapsedMs);
        
        if (estimatedTimeElement) {
            estimatedTimeElement.textContent = formatDuration(estimatedRemainingMs);
            estimatedTimeElement.className = 'time-value estimated';
        }
        
        // 计算预计完成时间
        if (completionTimeElement) {
            const completionTime = new Date(now.getTime() + estimatedRemainingMs);
            completionTimeElement.textContent = completionTime.toLocaleTimeString();
            completionTimeElement.className = 'time-value completion';
        }
    } else if (progress >= 100) {
        // 已完成
        if (estimatedTimeElement) {
            estimatedTimeElement.textContent = "00:00";
            estimatedTimeElement.className = 'time-value estimated';
        }
        
        if (completionTimeElement) {
            completionTimeElement.textContent = "已完成";
            completionTimeElement.className = 'time-value completion';
        }
    }
}

function updateStepHistory(currentStep, elapsedMs) {
    const lastStep = timeEstimationData.stepHistory[timeEstimationData.stepHistory.length - 1];
    
    if (!lastStep || lastStep.step !== currentStep) {
        // 新步骤开始
        if (lastStep) {
            // 完成上一步骤，记录实际用时
            const actualTime = elapsedMs - lastStep.startTime;
            updateAverageStepTime(lastStep.step, actualTime);
        }
        
        timeEstimationData.stepHistory.push({
            step: currentStep,
            startTime: elapsedMs
        });
    }
}

function updateAverageStepTime(step, actualTime) {
    if (!timeEstimationData.averageStepTimes[step]) {
        timeEstimationData.averageStepTimes[step] = actualTime;
    } else {
        // 使用指数移动平均
        const current = timeEstimationData.averageStepTimes[step];
        timeEstimationData.averageStepTimes[step] = 
            current * (1 - timeEstimationData.learningRate) + 
            actualTime * timeEstimationData.learningRate;
    }
}

function calculateSmartEstimate(progress, currentStep, elapsedMs) {
    // 基础时间估算（回退方案）
    const baseStepTimes = {
        1: 2 * 60 * 1000,   // 论文解析: 2分钟
        2: 5 * 60 * 1000,   // 内容生成: 5分钟
        3: 3 * 60 * 1000,   // 交互编辑: 3分钟
        4: 2 * 60 * 1000,   // 视频预览: 2分钟
        5: 1 * 60 * 1000,   // 反馈编辑: 1分钟
        6: 8 * 60 * 1000,   // 语音合成: 8分钟
        7: 3 * 60 * 1000,   // 音视频对齐: 3分钟
        8: 10 * 60 * 1000,  // 视频渲染: 10分钟
        9: 5 * 60 * 1000    // 最终合并: 5分钟
    };
    
    // 方法1：基于历史数据的智能估算
    if (Object.keys(timeEstimationData.averageStepTimes).length > 0) {
        let estimatedRemaining = 0;
        
        // 当前步骤剩余时间
        const currentStepHistory = timeEstimationData.stepHistory.find(h => h.step === currentStep);
        if (currentStepHistory) {
            const currentStepElapsed = elapsedMs - currentStepHistory.startTime;
            const avgStepTime = timeEstimationData.averageStepTimes[currentStep] || baseStepTimes[currentStep];
            const currentStepRemaining = Math.max(0, avgStepTime - currentStepElapsed);
            estimatedRemaining += currentStepRemaining;
        }
        
        // 未来步骤时间
        for (let step = currentStep + 1; step <= 9; step++) {
            const stepTime = timeEstimationData.averageStepTimes[step] || baseStepTimes[step];
            estimatedRemaining += stepTime;
        }
        
        return Math.max(0, estimatedRemaining);
    }
    
    // 方法2：基于进度的线性估算（改进版）
    if (progress > 5) {
        // 考虑不同阶段的速度变化
        const progressRate = progress / elapsedMs;
        const remainingProgress = 100 - progress;
        
        // 根据当前阶段调整估算
        let speedMultiplier = 1;
        if (currentStep >= 6) {
            speedMultiplier = 0.7; // 后期步骤通常较慢
        } else if (currentStep <= 3) {
            speedMultiplier = 1.2; // 前期步骤相对较快
        }
        
        const estimatedRemaining = (remainingProgress / progressRate) * speedMultiplier;
        return Math.max(0, estimatedRemaining);
    }
    
    // 方法3：基于步骤的固定估算（回退方案）
    let estimatedRemaining = 0;
    for (let step = currentStep; step <= 9; step++) {
        if (step === currentStep) {
            const stepProgress = getStepProgress(progress, step);
            const stepRemainingTime = baseStepTimes[step] * (1 - stepProgress);
            estimatedRemaining += stepRemainingTime;
        } else {
            estimatedRemaining += baseStepTimes[step];
        }
    }
    
    return Math.max(0, estimatedRemaining);
}

function getStepProgress(totalProgress, stepNumber) {
    // 获取当前选择的输出格式
    const outputFormat = document.getElementById('outputFormatSelect').value;
    
    // 定义不同格式下的步骤范围
    let stepRanges;
    
    if (outputFormat === 'markdown') {
        // Markdown格式只有3个步骤，每个步骤平均分配进度
        stepRanges = {
            1: { start: 0, end: 33 },
            2: { start: 33, end: 66 },
            3: { start: 66, end: 100 }
        };
    } else {
        // 视频格式使用原有的9个步骤
        stepRanges = {
            1: { start: 0, end: 20 },
            2: { start: 20, end: 40 },
            3: { start: 40, end: 60 },
            4: { start: 60, end: 70 },
            5: { start: 70, end: 75 },
            6: { start: 75, end: 85 },
            7: { start: 85, end: 92 },
            8: { start: 92, end: 97 },
            9: { start: 97, end: 100 }
        };
    }
    
    const range = stepRanges[stepNumber];
    if (!range) return 0;
    
    if (totalProgress <= range.start) return 0;
    if (totalProgress >= range.end) return 1;
    
    return (totalProgress - range.start) / (range.end - range.start);
}

function formatDuration(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 重置时间估算数据
function resetTimeEstimation() {
    timeEstimationData = {
        stepHistory: [],
        averageStepTimes: {},
        learningRate: 0.3
    };
    
    // 重置进度条和时间显示
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const elapsedTime = document.getElementById('elapsedTime');
    const estimatedTime = document.getElementById('estimatedTime');
    const completionTime = document.getElementById('completionTime');
    
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.classList.remove('completed', 'failed');
    }
    if (progressPercentage) {
        progressPercentage.textContent = '0%';
    }
    if (elapsedTime) {
        elapsedTime.textContent = '00:00';
    }
    if (estimatedTime) {
        estimatedTime.textContent = '--:--';
    }
    if (completionTime) {
        completionTime.textContent = '--:--';
    }
}

// 启动时间更新定时器
function startTimeUpdateTimer() {
    // 清除之前的定时器
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
    }
    
    // 重置时间估算数据
    resetTimeEstimation();
    
    // 每秒更新一次时间显示
    timeUpdateInterval = setInterval(() => {
        if (processingStartTime) {
            // 获取当前的真实状态数据或使用缓存的状态
            const currentStatusData = window.lastStatusData || {
                progress: 0,
                current_step: '处理中...'
            };
            updateTimeEstimate(currentStatusData);
        }
    }, 1000);
}

function updateStepsVisualization(statusData) {
    // 获取步骤容器中的步骤项
    const steps = document.querySelectorAll('.steps-container .step-item');
    
    if (!steps || steps.length === 0) {
        console.log('未找到步骤可视化元素');
        return;
    }
    
    // 清除所有步骤的状态
    steps.forEach(step => {
        step.classList.remove('active', 'completed', 'failed');
    });
    
    // 根据当前步骤和进度确定步骤状态
    let currentStepNumber = getCurrentStepNumber(statusData.current_step);
    
    steps.forEach((step, index) => {
        const stepNumber = index + 1;
        
        if (stepNumber < currentStepNumber) {
            step.classList.add('completed');
        } else if (stepNumber === currentStepNumber) {
            if (statusData.status === 'failed') {
                step.classList.add('failed');
            } else {
                step.classList.add('active');
            }
        }
    });
}

function getCurrentStepNumber(stepText) {
    // 获取当前选择的输出格式
    const outputFormat = document.getElementById('outputFormatSelect').value;
    
    // 如果是Markdown格式，使用简化的步骤映射
    if (outputFormat === 'markdown') {
        // Markdown格式只有3个步骤
        if (stepText.includes('论文处理') || stepText.includes('内容生成') || 
            stepText.includes('cover')) {
            return 2;
        } else if (stepText.includes('最终') || stepText.includes('音频合并') || 
                  stepText.includes('完成') || stepText.includes('✅')) {
            return 3;
        }
        return 1; // 默认第一步
    } else {
        // 视频格式使用原有的9个步骤映射
        if (stepText.includes('论文处理') || stepText.includes('内容生成')) {
            return 2;
        } else if (stepText.includes('cover')) {
            return 2;
        } else if (stepText.includes('交互式编辑')) {
            return 3;
        } else if (stepText.includes('预览')) {
            return 4;
        } else if (stepText.includes('反馈') || stepText.includes('编辑')) {
            return 5;
        } else if (stepText.includes('语音合成')) {
            return 6;
        } else if (stepText.includes('音视频对齐')) {
            return 7;
        } else if (stepText.includes('视频渲染')) {
            return 8;
        } else if (stepText.includes('音频合并') || stepText.includes('最终')) {
            return 9;
        } else if (stepText.includes('完成') || stepText.includes('✅')) {
            return 10; // 超过最后一步，表示全部完成
        }
        return 1; // 默认第一步
    }
}

function onProcessingComplete(statusData) {
    const cancelBtn = document.getElementById('cancelBtn');
    const activeProcessing = document.getElementById('activeProcessing');
    
    // 更新步骤可视化
    updateStepsVisualization(statusData);
    
    if (statusData.status === 'completed') {
        // 新增
        const outputFormat = (currentProcessing && currentProcessing.output_format) ? currentProcessing.output_format : 'video';

        // showSuccess('🎉 论文处理完成！');
        // 显示最终视频
        // showFinalVideo(statusData);

        // ---------------- 【核心修改点：根据格式显示不同结果】 -----------------
        if (outputFormat === 'markdown') {
            showSuccess('🎉 Markdown文档生成完成！');
            showFinalDocumentResult(statusData); // <--- 调用新的文档结果显示函数
        } else if (outputFormat === 'ppt') {
            showSuccess('🎉 PPT生成完成！');
            showFinalPPTResult(statusData); // <--- 调用新的PPT结果显示函数
        } else { // 默认是 video
            showSuccess('🎉 论文处理完成！');
            showFinalVideo(statusData);
        }
        // -------------------- 结果显示分流结束 ------------------------

        // 更新任务显示为完成状态
        if (activeProcessing) {
            const completedHtml = `
                <div class="task-completed">
                    <div class="completion-header">
                        <div class="completion-icon">✅</div>
                        <div class="completion-info">
                            <h4 class="task-title">处理完成</h4>
                            <div class="completion-time">完成时间: ${new Date().toLocaleString()}</div>
                        </div>
                    </div>
                    
                    <div class="completion-stats">
                        <div class="stat-item">
                            <span class="stat-label">总进度:</span>
                            <span class="stat-value">100%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">处理状态:</span>
                            <span class="stat-value success">成功完成</span>
                        </div>
                    </div>
                    
                    <div class="completion-actions">
                        <button class="btn btn-secondary" onclick="viewProcessingLogs('${statusData.process_id}')">
                            📋 查看详细日志
                        </button>
                        <button class="btn btn-outline" onclick="hideProcessingProgress()">
                            🗙 关闭
                        </button>
                    </div>
                </div>
            `;
            activeProcessing.innerHTML = completedHtml;
        }
        
        // activeProcessing 是指显示当前处理状态的那个大的div容器
        const activeProcessing = document.getElementById('activeProcessing');
        const taskTitleElement = activeProcessing.querySelector('.task-title');
        if (taskTitleElement) {
             taskTitleElement.textContent = `处理完成 (${outputFormat})`;
        }

        // 恢复原始按钮状态
        if (currentProcessing && currentProcessing.button) {
            currentProcessing.button.textContent = '✅ 处理完成';
            currentProcessing.button.disabled = false;
            currentProcessing.button.style.backgroundColor = '#28a745';
            currentProcessing.button.style.color = 'white';
        }
        
    } else if (statusData.status === 'failed') {
        showError(`❌ 处理失败: ${statusData.error || '未知错误'}`);
        
        // 更新任务显示为失败状态
        if (activeProcessing) {
            const failedHtml = `
                <div class="task-failed">
                    <div class="failure-header">
                        <div class="failure-icon">❌</div>
                        <div class="failure-info">
                            <h4 class="task-title">处理失败</h4>
                            <div class="failure-time">失败时间: ${new Date().toLocaleString()}</div>
                        </div>
                    </div>
                    
                    <div class="failure-reason">
                        <strong>失败原因:</strong> ${statusData.error || '未知错误'}
                    </div>
                    
                    <div class="failure-actions">
                        <button class="btn btn-warning" onclick="retryProcessing()">
                            🔄 重新处理
                        </button>
                        <button class="btn btn-secondary" onclick="viewProcessingLogs('${statusData.process_id}')">
                            📋 查看日志
                        </button>
                        <button class="btn btn-outline" onclick="hideProcessingProgress()">
                            🗙 关闭
                        </button>
                    </div>
                </div>
            `;
            activeProcessing.innerHTML = failedHtml;
        }
        
        // 恢复原始按钮状态
        if (currentProcessing && currentProcessing.button) {
            currentProcessing.button.textContent = '❌ 重新处理';
            currentProcessing.button.disabled = false;
            currentProcessing.button.style.backgroundColor = '#dc3545';
            currentProcessing.button.style.color = 'white';
        }
    }
    
    // 保留当前处理状态供查看结果使用
    // currentProcessing = null;
}

function viewProcessingResult(processId) {
    // 如果有最终视频，提供下载
    const downloadLink = document.createElement('a');
    downloadLink.href = `/download-result/${processId}`;
    downloadLink.download = `教学视频_${new Date().toISOString().slice(0,10)}.mp4`;
    downloadLink.click();
    
    showSuccess('🎬 开始下载教学视频...');
}

// 显示最终视频
function showFinalVideo(statusData) {
    const finalVideoContainer = document.getElementById('finalVideoContainer');
    const finalVideoPlayer = document.getElementById('finalVideoPlayer');
    const finalVideoSource = document.getElementById('finalVideoSource');
    const finalVideoFilename = document.getElementById('finalVideoFilename');
    const finalVideoStats = document.getElementById('finalVideoStats');
    const downloadVideoBtn = document.getElementById('downloadVideoBtn');
    
    if (finalVideoContainer && statusData.process_id) {
        // 确保视频播放器区域是可见的（可能之前被markdown模式隐藏了）
        const videoPlayerWrapper = document.querySelector('.video-player-wrapper');
        if (videoPlayerWrapper) {
            videoPlayerWrapper.style.display = 'block';
        }
        
        // 重置视频标题
        const videoHeaderTitle = document.querySelector('#finalVideoContainer .video-title');
        if (videoHeaderTitle) {
            videoHeaderTitle.textContent = '🎬 教学视频生成完成';
        }
        
        // 重置按钮区域为原始的下载按钮
        const videoActions = document.querySelector('.video-actions');
        if (videoActions) {
            videoActions.innerHTML = `
                <button class="btn btn-primary btn-large" id="downloadVideoBtn">
                    <span class="button-icon">📥</span>
                    <span class="button-text">下载教学视频</span>
                </button>
            `;
        }
        
        // 设置视频源
        const videoUrl = `/download-result/${statusData.process_id}`;
        finalVideoSource.src = videoUrl;
        finalVideoPlayer.load();
        
        // 设置文件信息
        const fileName = `教学视频_${new Date().toISOString().slice(0,10)}.mp4`;
        finalVideoFilename.textContent = fileName;
        
        // 重新获取下载按钮并设置点击事件
        const newDownloadBtn = document.getElementById('downloadVideoBtn');
        if (newDownloadBtn) {
            newDownloadBtn.onclick = () => {
                viewProcessingResult(statusData.process_id);
            };
        }
        
        // 显示视频容器
        finalVideoContainer.classList.remove('hidden');
        
        // 滚动到视频位置
        setTimeout(() => {
            finalVideoContainer.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }, 100);
        
        // 获取视频文件大小（可选）
        fetchVideoFileSize(videoUrl, finalVideoStats);
    }
}

// ... (showFinalVideo 函数)
// 【新增】显示最终文档结果
function showFinalDocumentResult(statusData) {
    // 获取处理状态卡片
    const processingStatusCard = document.getElementById('processingStatusCard');
    
    // 检查是否已经存在文档结果卡片，如果存在则移除
    const existingDocCard = document.getElementById('documentResultCard');
    if (existingDocCard) {
        existingDocCard.remove();
    }
    
    // 创建文档结果卡片
    const documentResultCard = document.createElement('div');
    documentResultCard.id = 'documentResultCard';
    documentResultCard.className = 'content-card document-result-card';
    documentResultCard.style.marginTop = '15px';
    
    // 设置卡片内容
    documentResultCard.innerHTML = `
        <div class="document-header">
            <h3 class="card-title">📝 文档生成完成</h3>
            <button class="close-btn" onclick="hideDocumentResult()" title="关闭">×</button>
        </div>
        <div class="document-content">
            <div class="document-info">
                <div class="document-meta">
                    <div class="document-filename">${(statusData.final_output_path || 'document.zip').split('/').pop()}</div>
                    <div class="document-stats">类型: Markdown文档 (ZIP)</div>
                </div>
                <div class="document-actions">
                    <button class="btn btn-outline btn-large" id="previewDocBtn" onclick="previewMarkdown('${statusData.process_id}')">
                        <span class="button-icon">👁️</span>
                        <span class="button-text">预览文档</span>
                    </button>
                    <button class="btn btn-primary btn-large" id="downloadDocBtn" onclick="window.location.href='/download-result/${statusData.process_id}'">
                        <span class="button-icon">📥</span>
                        <span class="button-text">下载文档 (.zip)</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 将结果卡片插入到处理状态卡片之后
    if (processingStatusCard && processingStatusCard.parentNode) {
        processingStatusCard.parentNode.insertBefore(documentResultCard, processingStatusCard.nextSibling);
    }
    
    // 平滑滚动到结果卡片
    setTimeout(() => {
        documentResultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

// 【新增】显示最终PPT结果
function showFinalPPTResult(statusData) {
    // 获取处理状态卡片
    const processingStatusCard = document.getElementById('processingStatusCard');
    
    // 检查是否已经存在PPT结果卡片，如果存在则移除
    const existingPPTCard = document.getElementById('pptResultCard');
    if (existingPPTCard) {
        existingPPTCard.remove();
    }
    
    // 创建PPT结果卡片
    const pptResultCard = document.createElement('div');
    pptResultCard.id = 'pptResultCard';
    pptResultCard.className = 'content-card ppt-result-card';
    pptResultCard.style.marginTop = '15px';
    
    // 设置卡片内容
    pptResultCard.innerHTML = `
        <div class="ppt-header">
            <h3 class="card-title">📊 PPT生成完成</h3>
            <button class="close-btn" onclick="hidePPTResult()" title="关闭">×</button>
        </div>
        <div class="ppt-content">
            <div class="ppt-info">
                <div class="ppt-meta">
                    <div class="ppt-filename">${(statusData.final_output_path || 'presentation.pptx').split('/').pop()}</div>
                    <div class="ppt-stats">类型: PowerPoint演示文稿 (.pptx)</div>
                </div>
                <div class="ppt-actions">
                    <button class="btn btn-primary btn-large" id="downloadPPTBtn" onclick="window.location.href='/download-result/${statusData.process_id}'">
                        <span class="button-icon">📥</span>
                        <span class="button-text">下载PPT文件</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 将结果卡片插入到处理状态卡片之后
    if (processingStatusCard && processingStatusCard.parentNode) {
        processingStatusCard.parentNode.insertBefore(pptResultCard, processingStatusCard.nextSibling);
    }
    
    // 平滑滚动到结果卡片
    setTimeout(() => {
        pptResultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

// 隐藏文档结果
function hideDocumentResult() {
    const documentResultCard = document.getElementById('documentResultCard');
    if (documentResultCard) {
        documentResultCard.remove();
    }
}

// 隐藏PPT结果
function hidePPTResult() {
    const pptResultCard = document.getElementById('pptResultCard');
    if (pptResultCard) {
        pptResultCard.remove();
    }
}

// 隐藏最终视频
function hideFinalVideo() {
    const finalVideoContainer = document.getElementById('finalVideoContainer');
    const finalVideoPlayer = document.getElementById('finalVideoPlayer');
    
    if (finalVideoContainer) {
        finalVideoContainer.classList.add('hidden');
        
        // 暂停视频播放
        if (finalVideoPlayer) {
            finalVideoPlayer.pause();
        }
    }
}

// 获取视频文件大小
async function fetchVideoFileSize(videoUrl, statsElement) {
    try {
        const response = await fetch(videoUrl, { method: 'HEAD' });
        const contentLength = response.headers.get('content-length');
        
        if (contentLength && statsElement) {
            const sizeInMB = (parseInt(contentLength) / 1024 / 1024).toFixed(2);
            statsElement.textContent = `文件大小: ${sizeInMB} MB`;
        }
    } catch (error) {
        console.log('无法获取视频文件大小:', error);
        if (statsElement) {
            statsElement.textContent = '文件大小: --';
        }
    }
}

function viewProcessingLogs(processId) {
    // 展开日志显示区域
    const logContent = document.getElementById('logContent');
    const logToggle = document.getElementById('logToggle');
    
    if (logContent && logContent.style.display === 'none') {
        logContent.style.display = 'block';
        if (logToggle) logToggle.textContent = '▼';
    }
    
    // 滚动到日志区域
    if (logContent) {
        logContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function retryProcessing() {
    if (currentProcessing) {
        // 重新启动处理
        startProcessing(currentProcessing.filename, currentProcessing.title);
    }
}

async function cancelProcessing() {
    if (currentProcessing) {
        // 停止轮询
        if (processingInterval) {
            clearInterval(processingInterval);
            processingInterval = null;
        }
        
        // 同时清除时间更新定时器
        if (timeUpdateInterval) {
            clearInterval(timeUpdateInterval);
            timeUpdateInterval = null;
        }
        
        // 恢复按钮状态
        if (currentProcessing.button) {
            currentProcessing.button.textContent = '开始处理';
            currentProcessing.button.disabled = false;
            currentProcessing.button.style.backgroundColor = '';
            currentProcessing.button.style.color = '';
        }
        
        // 隐藏处理状态卡片
        hideProcessingProgress();
        
        currentProcessing = null;
        showSuccess('✋ 已取消处理');
    }
}

// 显示反馈编辑界面
function showFeedbackEditingInterface(statusData) {
    const activeProcessing = document.getElementById('activeProcessing');
    
    if (activeProcessing) {
        const feedbackHtml = `
            <div class="feedback-editing-interface">
                <div class="feedback-header">
                    <div class="feedback-icon">💬</div>
                    <div class="feedback-info">
                        <h4 class="task-title">等待反馈编辑: ${currentProcessing ? currentProcessing.title : '未知文件'}</h4>
                        <div class="feedback-status">系统已生成预览视频，请进行反馈编辑</div>
                    </div>
                </div>
                
                <div class="feedback-description">
                    <p>📹 视频预览已生成，您可以：</p>
                    <ul>
                        <li>观看预览视频，评估教学效果</li>
                        <li>编辑代码文件，优化教学内容</li>
                        <li>修改讲稿文本，完善教学语言</li>
                        <li>提供反馈意见，改进教学质量</li>
                    </ul>
                </div>
                
                <div class="feedback-actions">
                    <button class="btn btn-primary feedback-editor-btn" onclick="openFeedbackEditor('${statusData.process_id}')">
                        🎬 打开反馈编辑器
                    </button>
                    <button class="btn btn-secondary" onclick="viewProcessingLogs('${statusData.process_id}')">
                        📋 查看处理日志
                    </button>
                </div>
                
                <div class="feedback-tips">
                    <div class="tip-item">
                        <span class="tip-icon">💡</span>
                        <span class="tip-text">编辑器将在新窗口中打开，包含视频预览和文件编辑功能</span>
                    </div>
                    <div class="tip-item">
                        <span class="tip-icon">⚠️</span>
                        <span class="tip-text">完成编辑后请点击"完成编辑"按钮继续处理流程</span>
                    </div>
                </div>
            </div>
        `;
        activeProcessing.innerHTML = feedbackHtml;
    }
}

// 打开反馈编辑器模态框
function openFeedbackEditor(processId) {
    const editorUrl = `/feedback-editor/${processId}`;
    const modal = document.getElementById('feedbackEditorModal');
    const iframe = document.getElementById('feedbackEditorIframe');
    const loading = document.getElementById('editorLoading');
    
    // 显示加载状态
    loading.style.display = 'block';
    iframe.style.display = 'none';
    
    // 显示模态框
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // 防止背景滚动
    
    // 设置iframe源
    iframe.src = editorUrl;
    
    // 监听iframe加载完成
    iframe.onload = function() {
        loading.style.display = 'none';
        iframe.style.display = 'block';
        showSuccess('🎬 反馈编辑器已加载完成');
    };
    
    // 监听编辑器消息
    window.addEventListener('message', function(event) {
        if (event.data.type === 'editor-finished') {
            // 编辑完成，关闭模态框并恢复状态轮询
            closeFeedbackEditor();
            showSuccess('✅ 反馈编辑完成，继续处理流程');
            
            // 恢复状态轮询
            if (!processingInterval) {
                startProcessingStatusPolling(processId);
            }
        } else if (event.data.type === 'editor-closed') {
            // 编辑器请求关闭
            closeFeedbackEditor();
        }
    });
    
    // 存储当前处理ID
    window.currentFeedbackProcessId = processId;
    
    showInfo('🎬 反馈编辑器已在弹窗中打开');
}

// 关闭反馈编辑器模态框
function closeFeedbackEditor() {
    const modal = document.getElementById('feedbackEditorModal');
    const iframe = document.getElementById('feedbackEditorIframe');
    
    // 隐藏模态框
    modal.classList.add('hidden');
    document.body.style.overflow = ''; // 恢复背景滚动
    
    // 清空iframe
    iframe.src = '';
    
    // 清除处理ID
    window.currentFeedbackProcessId = null;
    
    showInfo('📝 反馈编辑器已关闭');
}

// 完成反馈编辑
function finishFeedbackEditing() {
    const processId = window.currentFeedbackProcessId;
    
    if (!processId) {
        showError('❌ 无法获取处理任务ID');
        return;
    }
    
    if (confirm('确定完成反馈编辑并继续处理流程吗？')) {
        // 向iframe发送完成编辑消息
        const iframe = document.getElementById('feedbackEditorIframe');
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({ type: 'finish-editing' }, '*');
        }
        
        // 也可以直接调用API
        fetch(`/feedback-editor/finish/${processId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                closeFeedbackEditor();
                showSuccess('✅ 反馈编辑完成，继续处理流程');
                
                // 恢复状态轮询
                if (!processingInterval) {
                    startProcessingStatusPolling(processId);
                }
            } else {
                showError(data.error || '完成编辑失败');
            }
        })
        .catch(error => {
            showError('完成编辑失败: ' + error.message);
        });
    }
}

// 暴露处理相关的全局函数
window.startProcessing = startProcessing;
window.hideProcessingProgress = hideProcessingProgress;
window.minimizeProcessingStatus = minimizeProcessingStatus;
window.toggleLogDisplay = toggleLogDisplay;
window.cancelProcessing = cancelProcessing;
window.viewProcessingResult = viewProcessingResult;
window.viewProcessingLogs = viewProcessingLogs;
window.retryProcessing = retryProcessing;
window.openFeedbackEditor = openFeedbackEditor;
window.closeFeedbackEditor = closeFeedbackEditor;
window.finishFeedbackEditing = finishFeedbackEditing; 
window.clearLogContainer = clearLogContainer; 

// ========================= Web版交互编辑器功能 =========================

// 编辑器全局变量
let editorState = {
    currentProcessId: null,
    files: [],
    videos: [],
    openTabs: [],
    activeTab: null,
    unsavedChanges: {},
    originalContent: {},
    currentBackgroundFile: null
};

// 打开编辑器
async function openEditor(processId) {
    try {
        editorState.currentProcessId = processId;
        
        // 显示编辑器界面
        document.getElementById('editorCard').classList.remove('hidden');
        
        // 加载文件列表
        await loadEditorFiles();
        
        showSuccess('🚀 交互式编辑器已启动');
        
        // 滚动到编辑器
        document.getElementById('editorCard').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
    } catch (error) {
        showError(`启动编辑器失败: ${error.message}`);
        console.error('Open editor error:', error);
    }
}

// 加载文件列表
async function loadEditorFiles() {
    try {
        const response = await fetch(`/editor/files/${editorState.currentProcessId}`);
        const data = await response.json();
        
        if (data.success) {
            editorState.files = data.files;
            editorState.videos = data.page_videos || [];
            displayFileList(data.files, data.page_videos || []);
            updateEditorStatus(`已加载 ${data.total_count} 个文件和 ${data.video_count || 0} 个视频`);
            
            // 初始化文件分组状态
            setTimeout(initFileGroupStates, 100);
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        showError(`加载文件列表失败: ${error.message}`);
        displayEmptyFileList();
    }
}

// 显示文件列表
function displayFileList(files, videos = []) {
    const codeFileList = document.getElementById('codeFileList');
    const speechFileList = document.getElementById('speechFileList');
    const videoFileList = document.getElementById('videoFileList');
    const codeFileCount = document.getElementById('codeFileCount');
    const speechFileCount = document.getElementById('speechFileCount');
    const videoFileCount = document.getElementById('videoFileCount');
    
    if (files.length === 0 && videos.length === 0) {
        displayEmptyFileList();
        return;
    }
    
    // 分离Code和Speech文件
    const codeFiles = files.filter(file => file.type === 'Code');
    const speechFiles = files.filter(file => file.type === 'Speech');
    
    // 更新文件数量
    codeFileCount.textContent = codeFiles.length;
    speechFileCount.textContent = speechFiles.length;
    videoFileCount.textContent = videos.length;
    
    // 渲染Code文件列表
    if (codeFiles.length > 0) {
        codeFileList.innerHTML = codeFiles.map(file => {
            const sizeStr = formatFileSize(file.size);
            return `
                <div class="file-item file-type-code" onclick="openFileInEditor('${file.path}', '${file.filename}', '${file.type}')">
                    <div class="file-icon">🐍</div>
                    <div class="file-details">
                        <div class="file-name">${file.filename}</div>
                        <div class="file-meta">Python • ${sizeStr}</div>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        codeFileList.innerHTML = `
            <div class="empty-file-list">
                <div class="empty-icon">📄</div>
                <div>没有找到Python代码文件</div>
            </div>
        `;
    }
    
    // 渲染Speech文件列表
    if (speechFiles.length > 0) {
        speechFileList.innerHTML = speechFiles.map(file => {
            const sizeStr = formatFileSize(file.size);
            return `
                <div class="file-item file-type-speech" onclick="openFileInEditor('${file.path}', '${file.filename}', '${file.type}')">
                    <div class="file-icon">📝</div>
                    <div class="file-details">
                        <div class="file-name">${file.filename}</div>
                        <div class="file-meta">讲稿 • ${sizeStr}</div>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        speechFileList.innerHTML = `
            <div class="empty-file-list">
                <div class="empty-icon">📄</div>
                <div>没有找到讲稿文本文件</div>
            </div>
        `;
    }
    
    // 渲染Video文件列表
    if (videos.length > 0) {
        videoFileList.innerHTML = videos.map(video => {
            const sizeStr = formatFileSize(video.size);
            return `
                <div class="file-item video-file" onclick="openVideoInEditor('${video.filename}', '${video.type}')">
                    <div class="file-icon">🎬</div>
                    <div class="file-details">
                        <div class="file-name">${video.filename}</div>
                        <div class="file-meta">视频 • ${sizeStr}</div>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        videoFileList.innerHTML = `
            <div class="empty-file-list">
                <div class="empty-icon">🎬</div>
                <div>没有找到预览视频文件</div>
            </div>
        `;
    }
}

// 显示空文件列表
function displayEmptyFileList() {
    const codeFileList = document.getElementById('codeFileList');
    const speechFileList = document.getElementById('speechFileList');
    const videoFileList = document.getElementById('videoFileList');
    const codeFileCount = document.getElementById('codeFileCount');
    const speechFileCount = document.getElementById('speechFileCount');
    const videoFileCount = document.getElementById('videoFileCount');
    
    codeFileCount.textContent = '0';
    speechFileCount.textContent = '0';
    videoFileCount.textContent = '0';
    
    codeFileList.innerHTML = `
        <div class="empty-file-list">
            <div class="empty-icon">📂</div>
            <div>没有找到Python代码文件</div>
        </div>
    `;
    
    speechFileList.innerHTML = `
        <div class="empty-file-list">
            <div class="empty-icon">📂</div>
            <div>没有找到讲稿文本文件</div>
        </div>
    `;
    
    videoFileList.innerHTML = `
        <div class="empty-file-list">
            <div class="empty-icon">📂</div>
            <div>没有找到预览视频文件</div>
        </div>
    `;
}

// 切换文件分组的展开/折叠状态
function toggleFileGroup(groupType) {
    const fileList = document.getElementById(`${groupType}FileList`);
    const toggleBtn = document.getElementById(`${groupType}Toggle`);
    const toggleIcon = toggleBtn.querySelector('span');
    
    if (fileList.style.display === 'none') {
        fileList.style.display = 'block';
        toggleIcon.textContent = '−';
        localStorage.setItem(`fileGroup_${groupType}`, 'expanded');
    } else {
        fileList.style.display = 'none';
        toggleIcon.textContent = '+';
        localStorage.setItem(`fileGroup_${groupType}`, 'collapsed');
    }
}

// 初始化文件分组状态
function initFileGroupStates() {
    const codeState = localStorage.getItem('fileGroup_code') || 'expanded';
    const speechState = localStorage.getItem('fileGroup_speech') || 'expanded';
    const videoState = localStorage.getItem('fileGroup_video') || 'expanded';
    
    const codeFileList = document.getElementById('codeFileList');
    const speechFileList = document.getElementById('speechFileList');
    const videoFileList = document.getElementById('videoFileList');
    const codeToggle = document.getElementById('codeToggle');
    const speechToggle = document.getElementById('speechToggle');
    const videoToggle = document.getElementById('videoToggle');
    
    if (codeState === 'collapsed') {
        codeFileList.style.display = 'none';
        codeToggle.querySelector('span').textContent = '+';
    }
    
    if (speechState === 'collapsed') {
        speechFileList.style.display = 'none';
        speechToggle.querySelector('span').textContent = '+';
    }
    
    if (videoState === 'collapsed') {
        videoFileList.style.display = 'none';
        videoToggle.querySelector('span').textContent = '+';
    }
}

// 在编辑器中打开文件
async function openFileInEditor(filePath, filename, fileType) {
    try {
        // 检查是否已经打开
        const existingTab = editorState.openTabs.find(tab => tab.path === filePath);
        if (existingTab) {
            switchToTab(existingTab.id);
            return;
        }
        
        // 获取文件内容
        const response = await fetch('/editor/file-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_path: filePath
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 创建新标签
            const tabId = `tab_${Date.now()}`;
            const tab = {
                id: tabId,
                path: filePath,
                filename: filename,
                type: fileType,
                content: data.content,
                lineCount: data.line_count
            };
            
            editorState.openTabs.push(tab);
            editorState.originalContent[filePath] = data.content;
            
            // 显示标签
            updateEditorTabs();
            
            // 切换到新标签
            switchToTab(tabId);
            
            updateEditorStatus(`已打开文件: ${filename}`);
            
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        showError(`打开文件失败: ${error.message}`);
        console.error('Open file error:', error);
    }
}

// 更新编辑器标签
function updateEditorTabs() {
    const tabList = document.getElementById('editorTabs');
    
    if (editorState.openTabs.length === 0) {
        tabList.innerHTML = '';
        return;
    }
    
    tabList.innerHTML = editorState.openTabs.map(tab => {
        const icon = tab.type === 'Code' ? '🐍' : '📝';
        const isModified = editorState.unsavedChanges[tab.path];
        const activeClass = tab.id === editorState.activeTab ? 'active' : '';
        
        return `
            <div class="editor-tab ${activeClass}" onclick="switchToTab('${tab.id}')">
                <span>${icon}</span>
                <span>${tab.filename}${isModified ? '*' : ''}</span>
                <span class="close-tab" onclick="closeTab('${tab.id}', event)">×</span>
            </div>
        `;
    }).join('');
}

// 切换标签
function switchToTab(tabId) {
    const tab = editorState.openTabs.find(t => t.id === tabId);
    if (!tab) return;
    
    editorState.activeTab = tabId;
    
    // 隐藏欢迎界面，显示编辑器
    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('editorContainer').classList.remove('hidden');
    
    // 更新文件信息
    document.getElementById('currentFileName').textContent = tab.filename;
    document.getElementById('currentFileStats').textContent = `${tab.lineCount} 行 • ${tab.type}`;
    
    // 设置编辑器内容
    const editor = document.getElementById('codeEditor');
    editor.value = tab.content;
    
    // 更新标签显示
    updateEditorTabs();
    
    // 设置光标位置追踪
    setupEditorEvents();
    
    // 更新按钮状态
    updateEditorButtons();
}

// 关闭标签
function closeTab(tabId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const tabIndex = editorState.openTabs.findIndex(t => t.id === tabId);
    if (tabIndex === -1) return;
    
    const tab = editorState.openTabs[tabIndex];
    
    // 检查是否有未保存的更改
    if (editorState.unsavedChanges[tab.path]) {
        if (!confirm(`文件 "${tab.filename}" 有未保存的更改，确定要关闭吗？`)) {
            return;
        }
    }
    
    // 删除标签
    editorState.openTabs.splice(tabIndex, 1);
    delete editorState.unsavedChanges[tab.path];
    
    // 如果关闭的是当前标签
    if (editorState.activeTab === tabId) {
        if (editorState.openTabs.length > 0) {
            // 切换到其他标签
            const newActiveTab = editorState.openTabs[Math.max(0, tabIndex - 1)];
            switchToTab(newActiveTab.id);
        } else {
            // 显示欢迎界面
            editorState.activeTab = null;
            document.getElementById('welcomeScreen').classList.remove('hidden');
            document.getElementById('editorContainer').classList.add('hidden');
        }
    }
    
    updateEditorTabs();
}

// 设置编辑器事件
function setupEditorEvents() {
    const editor = document.getElementById('codeEditor');
    
    // 内容更改事件
    editor.oninput = function() {
        const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
        if (!activeTab) return;
        
        // 更新标签内容
        activeTab.content = editor.value;
        activeTab.lineCount = editor.value.split('\n').length;
        
        // 标记为已修改
        const isModified = editor.value !== editorState.originalContent[activeTab.path];
        editorState.unsavedChanges[activeTab.path] = isModified;
        
        // 更新界面
        updateEditorTabs();
        updateEditorButtons();
        updateFileStats();
        updateEditorStatus(isModified ? '已修改' : '已保存');
    };
    
    // 光标位置追踪
    editor.onselect = editor.onkeyup = editor.onclick = function() {
        updateCursorInfo();
    };
}

// 更新文件统计
function updateFileStats() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) return;
    
    document.getElementById('currentFileStats').textContent = 
        `${activeTab.lineCount} 行 • ${activeTab.type}`;
}

// 更新光标信息
function updateCursorInfo() {
    const editor = document.getElementById('codeEditor');
    const cursorPos = editor.selectionStart;
    const content = editor.value.substring(0, cursorPos);
    const lines = content.split('\n');
    const line = lines.length;
    const column = lines[lines.length - 1].length + 1;
    
    document.getElementById('cursorInfo').textContent = `行 ${line}, 列 ${column}`;
}

// 更新编辑器按钮状态
function updateEditorButtons() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) return;
    
    const saveBtn = document.getElementById('saveBtn');
    const isModified = editorState.unsavedChanges[activeTab.path];
    
    saveBtn.disabled = !isModified;
    
    // 更新AI编辑按钮
    const aiEditBtn = document.getElementById('aiEditBtn');
    if (aiEditBtn) {
        aiEditBtn.disabled = false; // 有活动标签时启用AI编辑按钮
    }
    
    // 更新状态显示
    const statusInfo = document.getElementById('editorStatus');
    if (isModified) {
        statusInfo.className = 'status-info status-modified';
        statusInfo.textContent = '已修改';
    } else {
        statusInfo.className = 'status-info status-saved';
        statusInfo.textContent = '已保存';
    }
}

// 保存当前文件
async function saveCurrentFile() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) return;
    
    try {
        updateEditorStatus('正在保存...');
        
        const response = await fetch('/editor/save-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_path: activeTab.path,
                content: activeTab.content
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 更新原始内容
            editorState.originalContent[activeTab.path] = activeTab.content;
            editorState.unsavedChanges[activeTab.path] = false;
            
            updateEditorTabs();
            updateEditorButtons();
            updateEditorStatus('保存成功');
            
            showSuccess(`✅ 已保存: ${activeTab.filename}`);
            
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        updateEditorStatus('保存失败', 'error');
        showError(`保存失败: ${error.message}`);
        console.error('Save file error:', error);
    }
}

// 撤销更改
function undoChanges() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) return;
    
    if (confirm(`确定要撤销对 "${activeTab.filename}" 的所有更改吗？`)) {
        // 恢复原始内容
        activeTab.content = editorState.originalContent[activeTab.path];
        activeTab.lineCount = activeTab.content.split('\n').length;
        
        // 更新编辑器
        document.getElementById('codeEditor').value = activeTab.content;
        
        // 清除修改标记
        editorState.unsavedChanges[activeTab.path] = false;
        
        updateEditorTabs();
        updateEditorButtons();
        updateFileStats();
        updateEditorStatus('已撤销更改');
        
        showSuccess('已撤销所有更改');
    }
}

// 搜索文件
async function searchEditorFiles() {
    const searchTerm = document.getElementById('fileSearchInput').value.trim();
    
    try {
        const response = await fetch('/editor/search-files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                process_id: editorState.currentProcessId,
                search_term: searchTerm
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayFileList(data.files);
            
            if (searchTerm) {
                updateEditorStatus(`搜索 "${searchTerm}": 找到 ${data.total_count} 个文件`);
            } else {
                updateEditorStatus(`显示所有文件: ${data.total_count} 个`);
            }
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        showError(`搜索失败: ${error.message}`);
        console.error('Search files error:', error);
    }
}

// 刷新文件列表
async function refreshEditorFiles() {
    await loadEditorFiles();
    showSuccess('文件列表已刷新');
}

// 处理背景图上传
async function handleBackgroundUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        updateBackgroundUploadInfo('正在上传...');
        
        const formData = new FormData();
        formData.append('background_file', file);
        formData.append('process_id', editorState.currentProcessId);
        
        const response = await fetch('/editor/upload-background', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            editorState.currentBackgroundFile = data.filename;
            updateBackgroundUploadInfo(`✅ ${data.filename} (${formatFileSize(data.size)})`);
            document.getElementById('applyBackgroundBtn').classList.remove('hidden');
            
            showSuccess(`背景图片上传成功: ${data.filename}`);
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        updateBackgroundUploadInfo('上传失败');
        showError(`上传背景图失败: ${error.message}`);
        console.error('Upload background error:', error);
    } finally {
        event.target.value = '';
    }
}

// 应用背景图到代码
async function applyBackgroundToCode() {
    if (!editorState.currentBackgroundFile) {
        showError('请先上传背景图片');
        return;
    }
    
    try {
        updateBackgroundUploadInfo('正在应用背景图...');
        
        const response = await fetch('/editor/apply-background', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                process_id: editorState.currentProcessId,
                background_file: editorState.currentBackgroundFile
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateBackgroundUploadInfo(`✅ 已应用到 ${data.modified_files} 个文件`);
            
            // 刷新已打开的代码文件
            await refreshOpenCodeFiles();
            
            showSuccess(`🎨 背景图已应用到 ${data.modified_files} 个代码文件`);
            
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        updateBackgroundUploadInfo('应用失败');
        showError(`应用背景图失败: ${error.message}`);
        console.error('Apply background error:', error);
    }
}

// 刷新已打开的代码文件
async function refreshOpenCodeFiles() {
    for (const tab of editorState.openTabs) {
        if (tab.type === 'Code') {
            try {
                const response = await fetch('/editor/file-content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_path: tab.path
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 更新原始内容
                    editorState.originalContent[tab.path] = data.content;
                    
                    // 如果用户没有修改过，更新显示内容
                    if (!editorState.unsavedChanges[tab.path]) {
                        tab.content = data.content;
                        tab.lineCount = data.line_count;
                        
                        // 如果是当前活动标签，更新编辑器
                        if (tab.id === editorState.activeTab) {
                            document.getElementById('codeEditor').value = tab.content;
                            updateFileStats();
                        }
                    }
                }
            } catch (error) {
                console.error(`刷新文件失败: ${tab.filename}`, error);
            }
        }
    }
    
    updateEditorTabs();
}

// 更新背景图上传信息
function updateBackgroundUploadInfo(message) {
    document.getElementById('backgroundUploadInfo').textContent = message;
}

// 更新编辑器状态
function updateEditorStatus(message, type = 'info') {
    const statusElement = document.getElementById('editorStatus');
    statusElement.textContent = message;
    statusElement.className = `status-info status-${type}`;
}

// 关闭编辑器
function closeEditor() {
    // 检查未保存的更改
    const unsavedFiles = Object.keys(editorState.unsavedChanges)
        .filter(path => editorState.unsavedChanges[path]);
    
    if (unsavedFiles.length > 0) {
        const fileNames = unsavedFiles.map(path => {
            const tab = editorState.openTabs.find(t => t.path === path);
            return tab ? tab.filename : path;
        });
        
        if (!confirm(`以下文件有未保存的更改：\n${fileNames.join('\n')}\n\n确定要关闭编辑器吗？`)) {
            return;
        }
    }
    
    // 重置编辑器状态
    editorState = {
        currentProcessId: null,
        files: [],
        openTabs: [],
        activeTab: null,
        unsavedChanges: {},
        originalContent: {},
        currentBackgroundFile: null
    };
    
    // 隐藏编辑器界面
    document.getElementById('editorCard').classList.add('hidden');
    
    showSuccess('📝 编辑器已关闭');
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ===== 新的处理阶段函数 =====

// 显示编辑界面
function showEditingInterface(statusData) {
    const uploadSuccessActions = document.getElementById('uploadSuccessActions');
    
    // 如果上传成功卡片存在，在其中显示编辑界面
    if (uploadSuccessActions && !uploadSuccessActions.classList.contains('hidden')) {
        // 更新卡片内容为编辑界面
        uploadSuccessActions.innerHTML = `
            <div class="upload-success-info">
                <div class="success-icon">📝</div>
                <div class="success-message">
                    <div class="success-title">交互式编辑</div>
                    <div class="success-filename">内容已生成，现在可以编辑代码和讲稿</div>
                </div>
            </div>
            
            <!-- 总体进度条 -->
            <div class="overall-progress">
                <div class="progress-header">
                    <div class="progress-title">总体进度</div>
                    <div class="progress-percentage" id="progressPercentage">${statusData.progress}%</div>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progressBar" style="width: ${statusData.progress}%"></div>
                </div>
            </div>
            
                    <!-- 步骤可视化 -->
        <div class="steps-container">
            <div class="step-item" data-step="1">
                <div class="step-icon">📄</div>
                <div class="step-text">论文解析者</div>
            </div>
            <div class="step-item" data-step="2">
                <div class="step-icon">🎬</div>
                <div class="step-text">内容生成员</div>
            </div>
            <div class="step-item" data-step="3">
                <div class="step-icon">🎥</div>
                <div class="step-text">视频预览员</div>
            </div>
            <div class="step-item" data-step="4">
                <div class="step-icon">💬</div>
                <div class="step-text">反馈编辑者</div>
            </div>
            <div class="step-item" data-step="5">
                <div class="step-icon">🎵</div>
                <div class="step-text">语音合成员</div>
            </div>
            <div class="step-item" data-step="6">
                <div class="step-icon">🔄</div>
                <div class="step-text">音视频对齐者</div>
            </div>
            <div class="step-item" data-step="7">
                <div class="step-icon">🎬</div>
                <div class="step-text">视频渲染员</div>
            </div>
            <div class="step-item" data-step="8">
                <div class="step-icon">🎦</div>
                <div class="step-text">最终合并者</div>
            </div>
        </div>
            
            <!-- 编辑按钮 -->
            <div class="edit-actions">
                <button class="btn btn-primary" onclick="startEditing('${statusData.process_id}')">
                    🖊️ 开始编辑代码和讲稿
                </button>
                <button class="btn btn-secondary" onclick="continueProcessing('${statusData.process_id}')">
                    ⏭️ 跳过编辑，直接继续
                </button>
            </div>
            
            <!-- 实时日志 -->
            <div class="log-container">
                <div class="log-header">
                    <span>处理日志</span>
                    <button class="log-toggle" onclick="toggleLogDisplay()" id="logToggle">▼</button>
                </div>
                <div class="log-content" id="logContent">
                    ${statusData.recent_logs ? statusData.recent_logs.slice(-10).map(log => 
                        `<div class="log-item">
                            <span class="log-message">${escapeHtml(log.message || '')}</span>
                        </div>`
                    ).join('') : '<div class="log-item"><span class="log-message">等待交互式编辑...</span></div>'}
                </div>
            </div>
        `;
        
        return;
    }
    
    // 如果没有上传成功卡片，使用原来的方式
    const activeProcessing = document.getElementById('activeProcessing');
    
    // 清理之前的日志容器
    clearLogContainer();
    
    activeProcessing.innerHTML = `
        <div class="edit-waiting-interface">
            <div class="edit-header">
                <div class="edit-icon">📝</div>
                <div class="edit-info">
                    <h4 class="edit-title">交互式编辑</h4>
                    <div class="edit-subtitle">内容已生成，现在可以编辑代码和讲稿</div>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${statusData.progress}%"></div>
                </div>
                <div class="progress-text">${statusData.progress}%</div>
            </div>
            
            <div class="edit-actions">
                <button class="btn btn-primary" onclick="startEditing('${statusData.process_id}')">
                    🖊️ 开始编辑代码和讲稿
                </button>
                <button class="btn btn-secondary" onclick="continueProcessing('${statusData.process_id}')">
                    ⏭️ 跳过编辑，直接继续
                </button>
            </div>
        </div>
    `;
    
    // 显示最近的日志 - 放在进度框框的下面
    if (statusData.recent_logs && statusData.recent_logs.length > 0) {
        const processingSteps = document.getElementById('processingSteps');
        const logSection = document.createElement('div');
        logSection.className = 'log-container';
        logSection.innerHTML = `
            <div class="log-header">
                <span>处理日志</span>
                <button class="log-toggle" onclick="toggleLogDisplay()" id="logToggle">▼</button>
            </div>
            <div class="log-content" id="logContent">
                ${statusData.recent_logs.slice(-10).map(log => 
                    `<div class="log-item">
                        <span class="log-message">${escapeHtml(log.message || '')}</span>
                    </div>`
                ).join('')}
            </div>
        `;
        // 将日志容器插入到进度框框的后面
        processingSteps.insertAdjacentElement('afterend', logSection);
    }
}

// 开始编辑
function startEditing(processId) {
    // 打开编辑器
    openEditor(processId);
}

// 继续处理
async function continueProcessing(processId) {
    try {
        showLoading('正在启动后续处理步骤...');
        
        const response = await fetch('/continue-processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                process_id: processId
            })
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showSuccess('后续处理已启动！');
            
            // 隐藏编辑界面，显示继续处理的进度
            showProcessingProgress(
                processId, 
                currentProcessing ? currentProcessing.title : '未知文件',
                currentProcessing ? currentProcessing.button : null
            );
            
            // 重新开始轮询状态
            startStatusPolling(processId);
            
        } else {
            showError(data.error || '启动后续处理失败');
        }
    } catch (error) {
        hideLoading();
        showError('启动后续处理失败: ' + error.message);
    }
}

// 暴露编辑器相关的全局函数
window.openEditor = openEditor;
window.refreshEditorFiles = refreshEditorFiles;
window.closeEditor = closeEditor;
window.openFileInEditor = openFileInEditor;
window.switchToTab = switchToTab;
window.closeTab = closeTab;
window.saveCurrentFile = saveCurrentFile;
window.undoChanges = undoChanges;
window.searchEditorFiles = searchEditorFiles;
window.handleBackgroundUpload = handleBackgroundUpload;
window.applyBackgroundToCode = applyBackgroundToCode;
window.toggleFileGroup = toggleFileGroup;

// 暴露新的函数
window.showEditingInterface = showEditingInterface;
window.startEditing = startEditing;
window.continueProcessing = continueProcessing; 

// 视频预览按钮控制
function updateVideoPreviewButton(processId, status) {
    const previewButtonContainer = document.getElementById('previewButtonContainer');
    const enterPreviewBtn = document.getElementById('enterPreviewBtn');
    
    if (!previewButtonContainer || !enterPreviewBtn) return;
    
    // 当预览视频可用时（处理进度达到55%或状态为waiting_feedback）显示按钮
    if ((status.progress >= 55 && status.stage === 'waiting_feedback') || 
        status.current_step.includes('预览')) {
        
        // 存储当前进程ID到按钮上，供点击时使用
        enterPreviewBtn.setAttribute('data-process-id', processId);
        previewButtonContainer.classList.remove('hidden');
    } else {
        previewButtonContainer.classList.add('hidden');
    }
}

// 打开视频预览功能
function openVideoPreview() {
    const enterPreviewBtn = document.getElementById('enterPreviewBtn');
    const processId = enterPreviewBtn.getAttribute('data-process-id');
    
    if (!processId) {
        showNotification('无法找到处理ID', 'error');
        return;
    }
    
    // 打开反馈编辑器模态框，显示预览视频
    const feedbackEditorModal = document.getElementById('feedbackEditorModal');
    const feedbackEditorIframe = document.getElementById('feedbackEditorIframe');
    const editorLoading = document.getElementById('editorLoading');
    
    if (feedbackEditorModal && feedbackEditorIframe) {
        // 设置iframe源
        feedbackEditorIframe.src = `/feedback-editor/${processId}`;
        
        // 显示加载动画
        if (editorLoading) editorLoading.style.display = 'flex';
        
        // 显示模态框
        feedbackEditorModal.classList.remove('hidden');
        
        // iframe加载完成后隐藏加载动画
        feedbackEditorIframe.onload = function() {
            if (editorLoading) editorLoading.style.display = 'none';
        };
    }
}

// 在原有的更新处理状态函数中调用预览按钮更新
function updateProcessingStatus(processId) {
    console.log(`手动更新处理状态: ${processId}`);
    
    // 发送API请求获取状态
    fetch(`/processing-status/${processId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 更新进度和视觉效果
                updateProcessingProgress(data);
                
                // 更新视频预览按钮状态
                updateVideoPreviewButton(processId, data);
                
                // 如果处理完成或失败，执行相应操作
                if (data.status === 'completed' || data.status === 'failed') {
                    onProcessingComplete(data);
                }
            } else {
                console.error('获取处理状态失败:', data.error || '未知错误');
            }
        })
        .catch(error => {
            console.error('获取处理状态失败:', error);
        });
}



// 暴露deleteContent函数供全局使用
window.deleteContent = deleteContent;

// ===== 视频预览相关函数 =====

// 打开视频预览
async function openVideoInEditor(filename, type) {
    try {
        // 隐藏编辑器容器，显示视频容器
        const editorContainer = document.getElementById('editorContainer');
        const videoContainer = document.getElementById('videoContainer');
        const welcomeScreen = document.getElementById('welcomeScreen');
        
        editorContainer.classList.add('hidden');
        welcomeScreen.classList.add('hidden');
        videoContainer.classList.remove('hidden');
        
        // 设置视频源
        const videoPlayer = document.getElementById('videoPlayer');
        const videoSource = document.getElementById('videoSource');
        const currentVideoName = document.getElementById('currentVideoName');
        const currentVideoStats = document.getElementById('currentVideoStats');
        
        // 构建视频URL
        const videoUrl = `/editor/page-video/${editorState.currentProcessId}/${filename}`;
        videoSource.src = videoUrl;
        videoPlayer.load();
        
        // 更新视频信息
        currentVideoName.textContent = filename;
        currentVideoStats.textContent = `视频文件`;
        
        // 获取并显示相关文件
        await loadRelatedFiles(filename);
        
        // 更新标签页
        updateVideoTab(filename);
        
        updateEditorStatus(`正在播放视频: ${filename}`);
        
    } catch (error) {
        showError(`打开视频失败: ${error.message}`);
    }
}

// 加载相关文件
async function loadRelatedFiles(videoFilename) {
    try {
        const response = await fetch(`/editor/page-associations/${editorState.currentProcessId}`);
        const data = await response.json();
        
        if (data.success) {
            const relatedFilesList = document.getElementById('relatedFilesList');
            const editRelatedBtn = document.getElementById('editRelatedBtn');
            
            // 找到当前视频的关联文件
            const baseName = videoFilename.replace('.mp4', '');
            const association = data.associations.find(assoc => assoc.base_name === baseName);
            
            if (association) {
                const relatedFiles = [];
                
                if (association.code_exists) {
                    relatedFiles.push({
                        filename: association.code_file,
                        type: 'Code',
                        icon: '🐍',
                        exists: true
                    });
                }
                
                if (association.speech_exists) {
                    relatedFiles.push({
                        filename: association.speech_file,
                        type: 'Speech',
                        icon: '📝',
                        exists: true
                    });
                }
                
                if (relatedFiles.length > 0) {
                    relatedFilesList.innerHTML = relatedFiles.map(file => `
                        <div class="related-file-item ${file.exists ? 'exists' : 'missing'}" 
                             onclick="openRelatedFile('${file.filename}', '${file.type}')">
                            <span class="related-file-icon">${file.icon}</span>
                            <span>${file.filename}</span>
                        </div>
                    `).join('');
                    
                    editRelatedBtn.disabled = false;
                    editRelatedBtn.setAttribute('data-video-base', baseName);
                } else {
                    relatedFilesList.innerHTML = `
                        <div class="related-file-item missing">
                            <span class="related-file-icon">❌</span>
                            <span>未找到相关文件</span>
                        </div>
                    `;
                    editRelatedBtn.disabled = true;
                }
            } else {
                relatedFilesList.innerHTML = `
                    <div class="related-file-item missing">
                        <span class="related-file-icon">❓</span>
                        <span>无法找到关联关系</span>
                    </div>
                `;
                editRelatedBtn.disabled = true;
            }
        }
        
    } catch (error) {
        console.error('加载相关文件失败:', error);
        const relatedFilesList = document.getElementById('relatedFilesList');
        relatedFilesList.innerHTML = `
            <div class="related-file-item missing">
                <span class="related-file-icon">❌</span>
                <span>加载相关文件失败</span>
            </div>
        `;
    }
}

// 打开相关文件
function openRelatedFile(filename, type) {
    // 查找文件路径
    const files = editorState.files;
    const file = files.find(f => f.filename === filename && f.type === type);
    
    if (file) {
        openFileInEditor(file.path, filename, type);
    } else {
        showError(`找不到文件: ${filename}`);
    }
}

// 编辑相关文件
function editRelatedFiles() {
    const editRelatedBtn = document.getElementById('editRelatedBtn');
    const videoBase = editRelatedBtn.getAttribute('data-video-base');
    
    if (videoBase) {
        // 查找相关的代码文件和讲稿文件
        const codeFile = editorState.files.find(f => f.filename === `${videoBase}_code.py`);
        const speechFile = editorState.files.find(f => f.filename === `${videoBase}_speech.txt`);
        
        if (codeFile) {
            openFileInEditor(codeFile.path, codeFile.filename, codeFile.type);
        } else if (speechFile) {
            openFileInEditor(speechFile.path, speechFile.filename, speechFile.type);
        } else {
            showError('未找到相关的可编辑文件');
        }
    }
}

// 更新视频标签页
function updateVideoTab(filename) {
    const editorTabs = document.getElementById('editorTabs');
    
    // 移除所有现有标签的活动状态
    const existingTabs = editorTabs.querySelectorAll('.tab-item');
    existingTabs.forEach(tab => tab.classList.remove('active'));
    
    // 检查是否已存在该视频的标签
    let existingTab = Array.from(existingTabs).find(tab => 
        tab.getAttribute('data-filename') === filename && 
        tab.getAttribute('data-type') === 'video'
    );
    
    if (!existingTab) {
        // 创建新的视频标签
        const tabItem = document.createElement('div');
        tabItem.className = 'tab-item active';
        tabItem.setAttribute('data-filename', filename);
        tabItem.setAttribute('data-type', 'video');
        
        tabItem.innerHTML = `
            <span class="tab-icon">🎬</span>
            <span class="tab-name">${filename}</span>
            <button class="tab-close" onclick="closeVideoTab('${filename}')">×</button>
        `;
        
        editorTabs.appendChild(tabItem);
    } else {
        existingTab.classList.add('active');
    }
}

// 关闭视频标签
function closeVideoTab(filename) {
    const editorTabs = document.getElementById('editorTabs');
    const tabToRemove = Array.from(editorTabs.children).find(tab => 
        tab.getAttribute('data-filename') === filename && 
        tab.getAttribute('data-type') === 'video'
    );
    
    if (tabToRemove) {
        tabToRemove.remove();
        
        // 如果关闭的是当前活动标签，显示欢迎屏幕
        if (tabToRemove.classList.contains('active')) {
            const videoContainer = document.getElementById('videoContainer');
            const welcomeScreen = document.getElementById('welcomeScreen');
            
            videoContainer.classList.add('hidden');
            welcomeScreen.classList.remove('hidden');
            
            // 停止视频播放
            const videoPlayer = document.getElementById('videoPlayer');
            videoPlayer.pause();
            videoPlayer.currentTime = 0;
        }
    }
}

// 全屏切换
function toggleFullscreen() {
    const videoPlayer = document.getElementById('videoPlayer');
    
    if (!document.fullscreenElement) {
        videoPlayer.requestFullscreen().catch(err => {
            console.error('无法进入全屏模式:', err);
        });
    } else {
        document.exitFullscreen();
    }
}

// 暴露视频相关函数供全局使用
window.openVideoInEditor = openVideoInEditor;
window.openRelatedFile = openRelatedFile;
window.editRelatedFiles = editRelatedFiles;
window.closeVideoTab = closeVideoTab;
window.toggleFullscreen = toggleFullscreen;

// 在同一个卡片中显示处理进度
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
    
    // 获取当前选择的输出格式
    const outputFormat = document.getElementById('outputFormatSelect').value;
    
    // 更新活动处理任务显示
    const activeProcessing = document.getElementById('activeProcessing');
    if (activeProcessing) {
        activeProcessing.innerHTML = `
            <div class="current-task">
                <!-- 任务标题、ID和时间信息已移除 -->
                
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    </div>
                </div>
                
                <!-- 取消按钮已移动到HTML中的该步骤进度卡片 -->
            </div>
        `;
    }
    
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
    
    // 修改步骤卡片，根据输出格式显示不同的步骤
    const stepsContainer = document.querySelector('.steps-container');
    if (stepsContainer) {
        if (outputFormat === 'markdown') {
            // Markdown格式只显示三个步骤
            stepsContainer.innerHTML = `
                <div class="step-item" data-step="1">
                    <div class="step-icon">📄</div>
                    <div class="step-text">论文解析者</div>
                </div>
                <div class="step-item" data-step="2">
                    <div class="step-icon">📝</div>
                    <div class="step-text">内容生成员</div>
                </div>
                <div class="step-item" data-step="3">
                    <div class="step-icon">🎦</div>
                    <div class="step-text">最终合并者</div>
                </div>
            `;
        } else {
            // 视频格式显示原有的9个步骤
            stepsContainer.innerHTML = `
                <div class="step-item" data-step="1">
                    <div class="step-icon">📄</div>
                    <div class="step-text">论文解析者</div>
                </div>
                <div class="step-item" data-step="2">
                    <div class="step-icon">🎬</div>
                    <div class="step-text">内容生成员</div>
                </div>
                <div class="step-item" data-step="3">
                    <div class="step-icon">📝</div>
                    <div class="step-text">交互编辑者</div>
                </div>
                <div class="step-item" data-step="4">
                    <div class="step-icon">🎥</div>
                    <div class="step-text">视频预览员</div>
                </div>
                <div class="step-item" data-step="5">
                    <div class="step-icon">💬</div>
                    <div class="step-text">反馈编辑者</div>
                </div>
                <div class="step-item" data-step="6">
                    <div class="step-icon">🎵</div>
                    <div class="step-text">语音合成员</div>
                </div>
                <div class="step-item" data-step="7">
                    <div class="step-icon">🔄</div>
                    <div class="step-text">音视频对齐者</div>
                </div>
                <div class="step-item" data-step="8">
                    <div class="step-icon">🎬</div>
                    <div class="step-text">视频渲染员</div>
                </div>
                <div class="step-item" data-step="9">
                    <div class="step-icon">🎦</div>
                    <div class="step-text">最终合并者</div>
                </div>
            `;
        }
    }
    
    // 滚动到状态卡片
    processingStatusCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // 重置时间估算数据和启动时间更新
    resetTimeEstimation();
    startTimeUpdateTimer();
}

// 从中央按钮开始处理

// ========================= Markdown预览功能 =========================

// 预览markdown文档
async function previewMarkdown(processId) {
    try {
        showLoading('正在加载文档预览...');
        
        // 设置全局变量供后续使用
        window.currentPreviewProcessId = processId;
        
        const response = await fetch(`/markdown-preview/${processId}`);
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            showMarkdownPreview(data);
        } else {
            showError(data.error || '获取文档预览失败');
        }
    } catch (error) {
        hideLoading();
        showError('网络错误，无法获取文档预览');
        console.error('Preview markdown error:', error);
    }
}

// 显示markdown预览界面
function showMarkdownPreview(data) {
    // 从当前URL或其他方式获取processId（需要在previewMarkdown函数中传递）
    const processId = window.currentPreviewProcessId || '';
    
    // 创建预览模态框
    const modalHtml = `
        <div class="markdown-preview-modal" id="markdownPreviewModal" data-process-id="${processId}">
            <div class="markdown-preview-container">
                <div class="markdown-preview-header">
                    <h3>📄 文档预览 - ${data.filename}</h3>
                    <button class="close-btn" onclick="closeMarkdownPreview()">×</button>
                </div>
                <div class="markdown-preview-content">
                    <div class="markdown-rendered" id="markdownContent"></div>
                </div>
                <div class="markdown-preview-footer">
                    <button class="btn btn-outline" onclick="closeMarkdownPreview()">关闭预览</button>
                    <button class="btn btn-primary" onclick="downloadMarkdownFromPreview('${data.filename}')">
                        <span class="button-icon">📥</span>
                        <span class="button-text">下载文档</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 渲染markdown内容
    const markdownContainer = document.getElementById('markdownContent');
    if (markdownContainer) {
        // 简单的markdown渲染
        let htmlContent = renderMarkdownToHtml(data.markdown_content, data.images);
        markdownContainer.innerHTML = htmlContent;
    }
    
    // 显示模态框
    const modal = document.getElementById('markdownPreviewModal');
    if (modal) {
        modal.style.display = 'flex';
        // 添加动画
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    }
}

// 简单的markdown渲染器
function renderMarkdownToHtml(markdownText, images = []) {
    // 创建图片映射
    const imageMap = {};
    images.forEach(img => {
        imageMap[img.filename] = img.data;
    });
    
    let html = markdownText
        // 标题
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        // 粗体和斜体
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // 行内代码
        .replace(/`(.*?)`/g, '<code>$1</code>')
        // 链接
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // 图片
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
            // 检查是否有对应的base64图片
            const filename = src.split('/').pop();
            if (imageMap[filename]) {
                return `<img src="${imageMap[filename]}" alt="${alt}" style="max-width: 100%; height: auto; margin: 10px 0;">`;
            }
            return `<img src="${src}" alt="${alt}" style="max-width: 100%; height: auto; margin: 10px 0;">`;
        });
    
    // 处理代码块
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // 处理换行
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // 包装段落
    html = '<p>' + html + '</p>';
    
    // 清理空段落
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[1-6]>.*?<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<pre>.*?<\/pre>)<\/p>/g, '$1');
    
    return html;
}

// 关闭markdown预览
function closeMarkdownPreview() {
    const modal = document.getElementById('markdownPreviewModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

// 从预览界面下载文档
function downloadMarkdownFromPreview(filename) {
    // 直接从模态框中的数据获取processId
    const modal = document.getElementById('markdownPreviewModal');
    if (modal && modal.dataset.processId) {
        window.location.href = `/download-result/${modal.dataset.processId}`;
    } else {
        // 备用方案：从文件名推断processId
        const processId = filename.replace(/_markdown\.zip$/, '').replace(/.*_/, '');
        window.location.href = `/download-result/${processId}`;
    }
}

// ========================= 智能体编辑功能 =========================

// 智能体编辑状态
let aiEditState = {
    originalCode: '',
    modifiedCode: '',
    editRequest: '',
    filename: '',
    isEditing: false
};

// 打开智能体编辑对话框
function openAiEditDialog() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) {
        showError('请先选择一个文件进行编辑');
        return;
    }

    // 只对代码文件启用智能体编辑
    if (!activeTab.filename.endsWith('.py') && !activeTab.filename.endsWith('.txt')) {
        showError('智能体编辑仅支持Python代码文件和文本文件');
        return;
    }

    // 保存当前状态
    aiEditState.originalCode = activeTab.content;
    aiEditState.filename = activeTab.filename;
    aiEditState.isEditing = false;

    // 重置界面
    document.getElementById('editRequestInput').value = '';
    document.getElementById('aiEditLoading').classList.add('hidden');
    document.getElementById('aiEditResult').classList.add('hidden');
    document.querySelector('.ai-edit-request').classList.remove('hidden');

    // 显示模态框
    document.getElementById('aiEditModal').classList.remove('hidden');
}

// 关闭智能体编辑对话框
function closeAiEditDialog() {
    document.getElementById('aiEditModal').classList.add('hidden');
    aiEditState = {
        originalCode: '',
        modifiedCode: '',
        editRequest: '',
        filename: '',
        isEditing: false
    };
}

// 提交智能体编辑请求
async function submitAiEdit() {
    const editRequest = document.getElementById('editRequestInput').value.trim();
    
    if (!editRequest) {
        showError('请输入修改需求');
        return;
    }

    aiEditState.editRequest = editRequest;
    aiEditState.isEditing = true;

    // 显示加载状态
    document.querySelector('.ai-edit-request').classList.add('hidden');
    document.getElementById('aiEditLoading').classList.remove('hidden');

    try {
        const response = await fetch('/editor/ai-edit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                original_code: aiEditState.originalCode,
                edit_request: editRequest,
                filename: aiEditState.filename
            })
        });

        const data = await response.json();

        if (data.success) {
            aiEditState.modifiedCode = data.modified_code;
            displayEditResult();
        } else {
            throw new Error(data.error);
        }

    } catch (error) {
        showError(`智能体编辑失败: ${error.message}`);
        console.error('AI edit error:', error);
        
        // 返回到输入界面
        document.getElementById('aiEditLoading').classList.add('hidden');
        document.querySelector('.ai-edit-request').classList.remove('hidden');
    }
}

// 显示编辑结果
function displayEditResult() {
    document.getElementById('aiEditLoading').classList.add('hidden');
    
    // 显示代码对比
    document.getElementById('originalCodePreview').textContent = aiEditState.originalCode;
    document.getElementById('modifiedCodePreview').textContent = aiEditState.modifiedCode;
    
    document.getElementById('aiEditResult').classList.remove('hidden');
}

// 应用AI修改
function applyAiChanges() {
    const activeTab = editorState.openTabs.find(t => t.id === editorState.activeTab);
    if (!activeTab) {
        showError('找不到活动标签');
        return;
    }

    // 更新编辑器内容
    activeTab.content = aiEditState.modifiedCode;
    activeTab.lineCount = aiEditState.modifiedCode.split('\n').length;
    
    // 更新编辑器显示
    document.getElementById('codeEditor').value = aiEditState.modifiedCode;
    
    // 标记为已修改
    editorState.unsavedChanges[activeTab.path] = true;
    
    // 更新界面
    updateEditorTabs();
    updateEditorButtons();
    updateEditorStatus('AI编辑完成');
    updateEditorStats();
    
    showSuccess(`✅ AI修改已应用到 ${activeTab.filename}`);
    
    // 关闭对话框
    closeAiEditDialog();
}

// 丢弃AI修改
function discardAiChanges() {
    if (confirm('确定要丢弃AI的修改建议吗？')) {
        closeAiEditDialog();
    }
}

// 重新编辑
function editAgain() {
    // 返回到输入界面
    document.getElementById('aiEditResult').classList.add('hidden');
    document.querySelector('.ai-edit-request').classList.remove('hidden');
    
    // 保留之前的输入内容
    document.getElementById('editRequestInput').focus();
}



// 将函数添加到全局作用域
window.openAiEditDialog = openAiEditDialog;
window.closeAiEditDialog = closeAiEditDialog;
window.submitAiEdit = submitAiEdit;
window.applyAiChanges = applyAiChanges;
window.discardAiChanges = discardAiChanges;
window.editAgain = editAgain;








// =================================================================
// 【新增】文件夹上传和侧边栏管理功能
// =================================================================

// =================================================================
// 【全新推荐】统一的上传模式管理逻辑
// =================================================================

// 存储原始的搜索框提示文字，以便恢复
const originalPlaceholder = document.getElementById('searchInput').placeholder;
// 存储当前的主输入框点击事件处理函数，以便移除
let currentInputClickHandler = null;

/**
 * 设置主输入框的模式（搜索、单篇上传、多篇上传）
 * @param {'search' | 'single' | 'folder'} mode - 要切换到的模式
 */
function setUploadMode(mode) {
    const searchInput = document.getElementById('searchInput');
    
    // 1. 清理：移除之前绑定的所有点击事件，防止重复触发
    if (currentInputClickHandler) {
        searchInput.removeEventListener('click', currentInputClickHandler);
        currentInputClickHandler = null;
    }
    // 恢复输入框的默认可输入状态
    searchInput.readOnly = false;
    searchInput.style.cursor = 'text';

    // 2. 根据模式进行配置
    switch (mode) {
        case 'single':
            // 切换到单篇上传模式
            searchInput.placeholder = "已切换到单篇上传模式，请点击此处选择PDF文件";
            searchInput.readOnly = true; // 设置为只读，防止用户输入文字
            searchInput.style.cursor = 'pointer'; // 鼠标变为手型
            
            currentInputClickHandler = () => {
                document.getElementById('pdfFileInput').click();
            };
            searchInput.addEventListener('click', currentInputClickHandler);
            break;

        case 'folder':
            // 切换到文件夹（论文集）上传模式
            searchInput.placeholder = "已切换到论文集上传模式，请点击此处选择文件夹";
            searchInput.readOnly = true;
            searchInput.style.cursor = 'pointer';

            currentInputClickHandler = () => {
                document.getElementById('folderInput').click();
            };
            searchInput.addEventListener('click', currentInputClickHandler);
            break;
            
        case 'search':
        default:
            // 恢复到默认的搜索模式
            searchInput.placeholder = originalPlaceholder;
            // 无需添加点击事件，恢复为普通输入框
            break;
    }
}

/**
 * 处理用户选择文件夹后的逻辑
 * @param {Event} event - 文件输入框的 onchange 事件
 */
function handleFolderUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) {
        console.log('用户取消了文件夹选择');
        return;
    }

    // 健壮性检查：只筛选出PDF文件
    const pdfFiles = Array.from(files).filter(file => file.name.toLowerCase().endsWith('.pdf'));

    if (pdfFiles.length === 0) {
        alert('您选择的文件夹中没有找到任何PDF文件！');
        // 恢复输入框状态
        setUploadMode('search');
        return;
    }

    // 通过 webkitRelativePath 获取文件夹名称
    const folderName = pdfFiles[0].webkitRelativePath.split('/')[0];
    
    // 使用 FormData 打包所有文件，准备发送到后端
    const formData = new FormData();
    formData.append('folder_name', folderName);
    pdfFiles.forEach(file => {
        // 'paper_files[]' 的 '[]' 对于Flask的 .getlist() 至关重要
        formData.append('paper_files[]', file, file.name); 
    });

    const loadingElement = document.getElementById('loading');
    loadingElement.textContent = `正在上传文件夹 "${folderName}"...`;
    loadingElement.classList.remove('hidden');

    // 发送到后端的 /upload-folder API
    fetch('/upload-folder', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 【请在这里加入下面这行代码】
        console.log('后端返回的原始数据:', data); 
        loadingElement.classList.add('hidden');
        if (data.success && data.files && data.files.length > 0) {
            console.log('文件夹上传成功:', data);
            // 【统一刷新】
            loadContentList(); 
            // 1. 在侧边栏创建可折叠的分组
            // addFolderToSidebar(data.folder_name, pdfFiles, data.batch_process_id);
            
            // 【确保传递了所有3个参数】
            addFolderToSidebar(data.folder_name, data.files, data.batch_process_id);
            
            showProcessingOptionsForFolder(data.folder_name, data.batch_process_id, data.files.length);


            // 2. 显示处理选项，并为"开始处理"按钮配置好多篇处理的逻辑
            // showProcessingOptionsForFolder(data.folder_name, data.batch_process_id, pdfFiles.length);

        } else {
            const errorMessage = data.error || '上传失败，但未收到明确错误信息。';
            alert('文件夹上传失败: ' + errorMessage);
        }
    })
    .catch(error => {
        loadingElement.classList.add('hidden');
        console.error('上传出错:', error);
        alert('上传过程中发生网络错误，请检查后端服务是否开启。');
    })
    .finally(() => {
        // 无论成功失败，都恢复输入框为默认搜索模式
        setUploadMode('search');
    });;
}


/**
 * 当文件夹上传成功后，更新UI并设置"开始处理"按钮的行为
 * @param {string} folderName - 文件夹名称
 * @param {string} batchId - 后端返回的批处理ID
 * @param {number} fileCount - 文件夹中的PDF文件数量
 */
/**
 * 当文件夹上传成功后，更新UI并设置"开始处理"按钮的行为
 * 【已修正】确保与单篇处理共享相同的UI更新和轮询逻辑
 * @param {string} folderName - 文件夹名称
 * @param {string} batchId - 后端返回的批处理ID
 * @param {number} fileCount - 文件夹中的PDF文件数量
 */
function showProcessingOptionsForFolder(folderName, batchId, fileCount) {
    const successActions = document.getElementById('uploadSuccessActions');
    const successTitle = document.querySelector('#uploadSuccessActions .success-title');
    const successFilename = document.getElementById('successFilename');
    const startBtn = document.getElementById('startProcessingBtn');

    // 更新UI以显示文件夹信息
    successTitle.textContent = '论文集上传成功！';
    successFilename.textContent = `文件夹: ${folderName} (共 ${fileCount} 篇论文)`;
    
    // 【核心】为"开始处理"按钮绑定处理文件夹的专属逻辑
    startBtn.onclick = () => {
        // 1. 从UI收集所有共享的配置参数（这部分与单篇处理完全一样）
        const outputFormat = document.getElementById('outputFormatSelect').value;
        const videoDuration = document.getElementById('modalVideoDurationSelect').value;
        const selectedVoiceElement = document.querySelector('.voice-option-item.selected');
        const voiceType = selectedVoiceElement ? selectedVoiceElement.dataset.voice : 'female';

        // 2. 创建 FormData 来发送处理请求
        const processData = new FormData();
        
        // 3. 添加文件夹特有的参数
        processData.append('folder_name', folderName);
        processData.append('batch_process_id', batchId);
        
        // 4. 添加所有共享的配置参数
        processData.append('output_format', outputFormat);
        processData.append('video_duration', videoDuration);
        processData.append('voice_type', voiceType);

        // 5. 检查并添加自定义音色文件和文本
        const voiceFileInput = document.getElementById('voiceUploadInput');
        if (voiceType === 'custom' && voiceFileInput.files.length > 0) {
            processData.append('voiceFile', voiceFileInput.files[0]);
            const voiceTextInput = document.getElementById('customVoiceText'); // 注意ID是否正确
            if (voiceTextInput) {
                processData.append('voiceText', voiceTextInput.value);
            }
        }
        
        console.log(`准备开始处理文件夹，ID: ${batchId}, 格式: ${outputFormat}`);

        // 6. 调用后端API开始处理整个文件夹
        fetch('/start-folder-processing', {
            method: 'POST',
            body: processData
        })
        .then(res => res.json())
        .then(result => {
            // 【重点修改在这里！】
            if (result.success && result.process_id) {
                showSuccess(`开始处理论文集: ${folderName}`);

                // a. 像单篇处理一样，保存当前处理任务的信息
                currentProcessing = {
                    processId: result.process_id,
                    filename: folderName, // 对于多篇，我们用文件夹名
                    title: `论文集: ${folderName}`,
                    button: startBtn,
                    output_format: outputFormat
                };
                
                // b. 像单篇处理一样，调用函数来显示处理中的UI卡片
                //    这里我们复用 showProcessingInSameCard，因为它能创建我们需要的UI结构
                showProcessingInSameCard(result.process_id, `论文集: ${folderName}`);

                // c. 像单篇处理一样，用返回的 process_id 启动状态轮询！
                startStatusPolling(result.process_id);

            } else {
                alert("启动文件夹处理失败: " + (result.error || '未知错误'));
            }
        })
        .catch(error => {
            console.error('启动文件夹处理时发生网络错误:', error);
            alert('启动处理失败，请检查网络连接和后端服务。');
        });
    };

    // 显示包含"开始处理"按钮的面板
    successActions.classList.remove('hidden');
}

// /**
//  * 在侧边栏中添加一个新的、可折叠的文件夹分组
//  * @param {string} folderName - 文件夹的名称
//  * @param {FileList} fileList - 上传的文件列表
//  * @param {string} batchId - 这个批次任务的唯一ID
//  */
// function addFolderToSidebar(folderName, fileList, batchId) {
//     const contentSections = document.getElementById('contentSections');
//     if (!contentSections) return;

//     const groupDiv = document.createElement('div');
//     groupDiv.className = 'sidebar-group';
//     groupDiv.setAttribute('data-batch-id', batchId);
//     groupDiv.setAttribute('data-folder-name', folderName);

//     const headerDiv = document.createElement('div');
//     headerDiv.className = 'sidebar-group-header';
//     headerDiv.onclick = () => toggleSidebarGroup(headerDiv);
//     headerDiv.innerHTML = `
//         <span class="toggle-icon">▼</span>
//         <span class="group-title">📁 ${folderName}</span>
//         <span class="group-file-count">${fileList.length}</span>
//     `;

//     const contentDiv = document.createElement('div');
//     contentDiv.className = 'sidebar-group-content';

//     fileList.forEach(file => {
//         const itemDiv = document.createElement('div');
//         itemDiv.className = 'sidebar-item';
//         itemDiv.setAttribute('data-filename', file.name);
//         itemDiv.innerHTML = `
//             <span class="item-icon">📄</span>
//             <span class="item-title">${file.name}</span>
//         `;
//         contentDiv.appendChild(itemDiv);
//     });
    
//     groupDiv.appendChild(headerDiv);
//     groupDiv.appendChild(contentDiv);
//     contentSections.prepend(groupDiv);

//     // 默认展开新添加的组
//     setTimeout(() => {
//         contentDiv.style.maxHeight = contentDiv.scrollHeight + "px";
//         headerDiv.querySelector('.toggle-icon').style.transform = 'rotate(0deg)';
//     }, 100);
// }
/**
 * 【全新版本】在侧边栏添加一个完整的、可折叠的文件夹分组
 * @param {string} folderName - 文件夹名称
 * @param {Array<Object>} filesData - 文件信息数组 [{original_name, saved_name}]
 * @param {string} batchId - 整个文件夹的批处理ID
 */
function addFolderToSidebar(folderName, filesData, batchId) {
    const contentSections = document.getElementById('contentSections');
    if (!contentSections) return;

    // 1. 创建最外层的分组容器
    const groupDiv = document.createElement('div');
    groupDiv.className = 'sidebar-group';
    groupDiv.setAttribute('data-batch-id', batchId);

    // 2. 创建文件夹头部 (看起来像一个 content-item)
    const headerDiv = document.createElement('div');
    headerDiv.className = 'sidebar-group-header';
    headerDiv.onclick = function() { toggleSidebarGroup(this); }; // 点击头部时折叠/展开
    headerDiv.innerHTML = `
        <div class="content-title">
            <span class="toggle-icon">▼</span>
            <span>📁</span>
            <span title="${folderName}">${folderName}</span>
        </div>
        <div class="content-actions">
            <button class="delete-btn" onclick="deleteFolder('${batchId}', event)" title="删除整个文件夹">🗑️</button>
        </div>
    `;

    // 3. 创建用于容纳子项的、可折叠的内容区域
    const contentDiv = document.createElement('div');
    contentDiv.className = 'sidebar-group-content';

    // 4. 遍历文件列表，为每个文件创建子卡片
    filesData.forEach(fileInfo => {
        const itemDiv = document.createElement('div');
        // 使用 content-item 样式，并添加一个子项的特定类用于缩进
        itemDiv.className = 'content-item'; 
        itemDiv.innerHTML = `
            <div class="content-title" title="${fileInfo.original_name}">${fileInfo.original_name}</div>
            <div class="content-actions">
                <button class="preview-btn" onclick="previewContent('${fileInfo.saved_name}', 'pdf')">预览</button>
                <button class="delete-btn" onclick="deleteContent('${fileInfo.saved_name}', 'pdf')" title="删除">🗑️</button>
            </div>
        `;
        contentDiv.appendChild(itemDiv);
    });

    // 5. 将头部和内容区组装到主容器中
    groupDiv.appendChild(headerDiv);
    groupDiv.appendChild(contentDiv);

    // 6. 将完整的分组添加到侧边栏顶部
    contentSections.prepend(groupDiv);
}


// /**
//  * 切换侧边栏分组的展开/折叠状态
//  * @param {HTMLElement} headerElement - 被点击的组头部元素
//  */
// function toggleSidebarGroup(headerElement) {
//     const groupContent = headerElement.nextElementSibling;
//     const toggleIcon = headerElement.querySelector('.toggle-icon');

//     if (groupContent.style.maxHeight && groupContent.style.maxHeight !== '0px') {
//         groupContent.style.maxHeight = '0px';
//         toggleIcon.style.transform = 'rotate(-90deg)';
//     } else {
//         groupContent.style.maxHeight = groupContent.scrollHeight + "px";
//         toggleIcon.style.transform = 'rotate(0deg)';
//     }
// }
// /**
//  * 【新增】处理文件夹折叠/展开的函数
//  * @param {HTMLElement} headerElement - 被点击的文件夹头部元素
//  */
// function toggleSidebarGroup(headerElement) {
//     headerElement.classList.toggle('expanded');
//     const content = headerElement.nextElementSibling;
//     if (content.style.maxHeight && content.style.maxHeight !== '0px') {
//         content.style.maxHeight = '0px';
//     } else {
//         // 设置为内容的实际高度以展开
//         content.style.maxHeight = content.scrollHeight + "px";
//     }
// }

/**
 * 【最终优化版】处理文件夹折叠/展开的函数
 * @param {HTMLElement} headerElement - 被点击的文件夹头部元素
 */
function toggleSidebarGroup(headerElement) {
    const content = headerElement.nextElementSibling;

    // 1. 同时给头部和内容区切换 'expanded' 类
    headerElement.classList.toggle('expanded');
    content.classList.toggle('expanded');

    // 2. 使用更健壮的方式设置 max-height
    // 检查内联样式中是否已有 max-height 值
    if (content.style.maxHeight) {
        // 如果有（代表已展开），则设为 null 来清除内联样式，交由CSS的 max-height: 0; 来折叠
        content.style.maxHeight = null;
    } else {
        // 如果没有（代表已折叠），则设置为其内容所需的确切高度来展开
        content.style.maxHeight = content.scrollHeight + "px";
    }
}

/**
 * 【无需修改，保持此版本】处理删除整个文件夹的函数
 * @param {string} batchId - 文件夹的批处理ID
 * @param {Event} event - 点击事件对象
 */
function deleteFolder(batchId, event) {
    // 阻止事件冒泡，防止点击删除按钮时触发折叠/展开
    event.stopPropagation();

    if (confirm(`您确定要删除这个文件夹及其所有内容吗？`)) {
        fetch('/delete-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_process_id: batchId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const groupToRemove = document.querySelector(`.sidebar-group[data-batch-id="${batchId}"]`);
                if (groupToRemove) {
                    groupToRemove.remove();
                }
            } else {
                alert('删除失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(error => console.error('删除文件夹时出错:', error));
    }
}



// 【修改建议】修改您现有的 `handlePdfUpload` 函数，使其也使用一个独立的UI更新函数
// 这样可以让逻辑更清晰
// function handlePdfUpload(event) {
//     // ... 您现有的上传逻辑 ...
//     // 在 fetch(...).then(...) 成功的回调中，调用一个新的函数
//     // showProcessingOptionsForFile(data.filename, data.process_id);
// }

// 您可以创建一个 showProcessingOptionsForFile 函数来专门处理单文件的情况，
// 这会让您的代码库更加模块化和易于维护。