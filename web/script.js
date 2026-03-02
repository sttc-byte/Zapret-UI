const THEMES = {
    amoled: { bgMain: '#000000', bgPanel: 'rgba(10, 10, 10, 0.6)', border: 'rgba(255, 255, 255, 0.1)', textMain: '#ffffff', textMuted: '#888888', accentBg: '#ffffff', accentTxt: '#000000', blur: '20' },
    dark: { bgMain: '#0f1115', bgPanel: 'rgba(22, 25, 32, 0.7)', border: 'rgba(255, 255, 255, 0.08)', textMain: '#e2e8f0', textMuted: '#718096', accentBg: '#60a5fa', accentTxt: '#ffffff', blur: '20' },
    light: { bgMain: '#e2e8f0', bgPanel: 'rgba(255, 255, 255, 0.6)', border: 'rgba(0, 0, 0, 0.1)', textMain: '#0f172a', textMuted: '#475569', accentBg: '#0f172a', accentTxt: '#ffffff', blur: '20' },
    custom: { bgMain: '#000000', bgPanel: 'rgba(10, 10, 10, 0.6)', border: 'rgba(255, 255, 255, 0.1)', textMain: '#ffffff', textMuted: '#aaaaaa', accentBg: '#ff0000', accentTxt: '#ffffff', blur: '20' }
};

window.onload = async function() {
    await reloadBatList();

    let settings = await eel.get_settings()();
    
    document.getElementById("set-autostart").checked = settings.autostart || false;
    document.getElementById("set-minimized").checked = settings.start_minimized || false;
    if(settings.zapret_path) { document.getElementById("set-path").value = settings.zapret_path; }

    let status = await eel.get_status()();
    update_status(status);

    document.getElementById("theme-selector").value = settings.theme || "amoled";
    document.getElementById("custom-color-picker").value = settings.custom_color || "#ff0000";
    document.getElementById("custom-bg-color-picker").value = settings.custom_bg_color || "#050505";
    document.getElementById("custom-text-color-picker").value = settings.custom_text_color || "#ffffff";
    document.getElementById("custom-muted-color-picker").value = settings.custom_muted_color || "#aaaaaa";
    document.getElementById("custom-alpha-slider").value = settings.custom_alpha || "0.6";
    document.getElementById("custom-blur-slider").value = settings.custom_blur || "20";
    
    applyTheme(false); 

    let savedIconColor = settings.tray_color || "#9b59b6";
    let iconColorPicker = document.getElementById("icon-color-picker");
    if(iconColorPicker) iconColorPicker.value = savedIconColor;
    setDynamicIconColor(savedIconColor, false);

    // Подтягиваем сохраненное состояние для тумблера прозрачной рамки
    let isTrans = settings.transparent_frame !== undefined ? settings.transparent_frame : true; 
    let frameToggle = document.getElementById("set-transparent-frame");
    if(frameToggle) frameToggle.checked = isTrans;
    
    let frameColor = document.getElementById("frame-color-picker");
    if(frameColor) frameColor.value = settings.frame_color || "#050505";
    
    setTimeout(() => { toggleFrameMode(); }, 500);

    if (settings.logs_hidden) {
        document.getElementById("logs-container").style.display = "none";
        document.getElementById("btn-log-toggle").innerText = "ПОКАЗАТЬ ▼";
        window.resizeTo(480, 730); 
    } else {
        window.resizeTo(480, 890);
    }
};

let resizeTimer;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
        let isHidden = document.getElementById("logs-container").style.display === "none";
        let activeTab = document.querySelector('.nav-btn.active');
        let height = 890;
        if (activeTab && activeTab.innerText === "УПРАВЛЕНИЕ") {
            height = isHidden ? 730 : 890;
        }
        if (window.innerWidth !== 480 || window.innerHeight !== height) {
            window.resizeTo(480, height);
        }
    }, 200); 
});

function applyTheme(saveToConfig = true) {
    let themeKey = document.getElementById("theme-selector").value;
    let customAccent = document.getElementById("custom-color-picker").value;
    let customBg = document.getElementById("custom-bg-color-picker").value;
    let customText = document.getElementById("custom-text-color-picker").value;
    let customMuted = document.getElementById("custom-muted-color-picker").value;
    let customAlpha = document.getElementById("custom-alpha-slider").value;
    let customBlur = document.getElementById("custom-blur-slider").value;
    
    if (saveToConfig) {
        eel.save_settings({
            "theme": themeKey, "custom_color": customAccent, "custom_bg_color": customBg,
            "custom_text_color": customText, "custom_muted_color": customMuted,
            "custom_alpha": customAlpha, "custom_blur": customBlur
        })();
    }

    let t = THEMES[themeKey];
    let root = document.documentElement;

    if (themeKey === 'custom') {
        document.getElementById("custom-theme-box").style.display = "block";
        loadBgImage(); 
        
        root.style.setProperty('--bg-main', customBg);
        root.style.setProperty('--bg-panel', `rgba(10, 10, 10, ${customAlpha})`);
        root.style.setProperty('--border-color', `rgba(255, 255, 255, ${customAlpha * 0.3})`);
        root.style.setProperty('--text-main', customText);
        root.style.setProperty('--text-muted', customMuted); 
        root.style.setProperty('--accent-bg', customAccent);
        root.style.setProperty('--blur-amount', customBlur + 'px');
        
        let hex = customAccent.replace('#', '');
        let r = parseInt(hex.substr(0, 2), 16); let g = parseInt(hex.substr(2, 2), 16); let b = parseInt(hex.substr(4, 2), 16);
        let yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        root.style.setProperty('--accent-text', (yiq >= 128) ? '#000000' : '#ffffff');
    } else {
        document.getElementById("custom-theme-box").style.display = "none";
        document.body.style.backgroundImage = "none";
        
        root.style.setProperty('--bg-main', t.bgMain);
        root.style.setProperty('--bg-panel', t.bgPanel);
        root.style.setProperty('--border-color', t.border);
        root.style.setProperty('--text-main', t.textMain);
        root.style.setProperty('--text-muted', t.textMuted);
        root.style.setProperty('--accent-bg', t.accentBg);
        root.style.setProperty('--accent-text', t.accentTxt);
        root.style.setProperty('--blur-amount', t.blur + 'px');
    }
    
    let toggle = document.getElementById("set-transparent-frame");
    if (toggle && toggle.checked) { syncFrameWithBackground(); }
}

async function setCustomBgImage() {
    let success = await eel.pick_bg_image()();
    if(success) { applyTheme(false); } 
}

async function resetCustomBgImage() {
    await eel.clear_bg_image()();
    document.body.style.backgroundImage = "none";
}

async function loadBgImage() {
    let b64 = await eel.get_bg_image_base64()();
    if(b64) { document.body.style.backgroundImage = `url('${b64}')`; } 
    else { document.body.style.backgroundImage = "none"; }
}

async function reloadBatList() {
    let batFiles = await eel.get_bat_files()();
    let selector = document.getElementById("bat-selector");
    selector.innerHTML = "";
    batFiles.forEach(file => {
        let option = document.createElement("option");
        option.text = file; option.value = file; selector.add(option);
    });
    let lastBat = await eel.get_last_bat()();
    if (lastBat && batFiles.includes(lastBat)) { selector.value = lastBat; }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active-tab'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active-tab');
    event.target.classList.add('active');
    
    if(tabId !== 'main') {
        window.resizeTo(480, 890);
    } else {
        let isHidden = document.getElementById("logs-container").style.display === "none";
        if(isHidden) { window.resizeTo(480, 730); } else { window.resizeTo(480, 890); }
    }
}

function toggleLogs() {
    let container = document.getElementById("logs-container");
    let btn = document.getElementById("btn-log-toggle");
    if (container.style.display === "none") {
        container.style.display = "block"; btn.innerText = "СКРЫТЬ ▲"; 
        eel.save_settings({"logs_hidden": false})();
        window.resizeTo(480, 890); 
    } else {
        container.style.display = "none"; btn.innerText = "ПОКАЗАТЬ ▼"; 
        eel.save_settings({"logs_hidden": true})();
        window.resizeTo(480, 730); 
    }
}

eel.expose(add_log);
function add_log(msg) {
    let logBox = document.getElementById("log-box");
    let time = new Date().toLocaleTimeString();
    logBox.value += `[${time}] ${msg}\n`; logBox.scrollTop = logBox.scrollHeight;
}

function saveSelection() { eel.save_last_bat(document.getElementById("bat-selector").value); }
async function startEngine() { await eel.toggle_engine(document.getElementById("bat-selector").value)(); }

eel.expose(update_status);
function update_status(isActive) {
    let statusSpan = document.getElementById("status");
    let btn = document.getElementById("btn-toggle");
    if(isActive) {
        statusSpan.innerText = "АКТИВЕН"; statusSpan.style.color = "var(--accent-bg)";
        btn.innerText = "ОСТАНОВИТЬ"; btn.classList.add("active-btn");
    } else {
        statusSpan.innerText = "ВЫКЛЮЧЕН"; statusSpan.style.color = "var(--text-muted)";
        btn.innerText = "ЗАПУСТИТЬ ОБХОД"; btn.classList.remove("active-btn");
    }
}

async function runNetTest() {
    let elPing = document.getElementById("stat-ping");
    elPing.innerText = "ЗАМЕРЯЕМ..."; elPing.className = "ping-text gray"; 
    await eel.start_diagnostics()();
}

eel.expose(update_diagnostics);
function update_diagnostics(ds, yt, ping) {
    let elDs = document.getElementById("stat-ds"); let elYt = document.getElementById("stat-yt"); let elPing = document.getElementById("stat-ping");
    elDs.innerText = "Discord: " + (ds ? "ДОСТУПЕН" : "БЛОК"); elDs.className = ds ? "" : "gray"; 
    elYt.innerText = "YouTube: " + (yt ? "ДОСТУПЕН" : "БЛОК"); elYt.className = yt ? "" : "gray";
    elPing.innerText = "Пинг: " + ping + (ping !== "ОШИБКА" ? " мс" : ""); elPing.className = ping !== "ОШИБКА" ? "ping-text" : "ping-text gray";
}

async function startScanner() {
    let btn = document.getElementById("btn-scan");
    btn.innerText = "СКАНИРОВАНИЕ..."; btn.disabled = true; btn.style.opacity = "0.5";
    document.getElementById("tuner-log").value = ""; 
    await eel.start_scanner()();
}

eel.expose(tuner_print);
function tuner_print(msg) {
    let logBox = document.getElementById("tuner-log");
    logBox.value += msg + "\n"; logBox.scrollTop = logBox.scrollHeight;
}

eel.expose(scanner_finished);
function scanner_finished(best_bat) {
    let btn = document.getElementById("btn-scan");
    btn.innerText = "НАЧАТЬ СКАНИРОВАНИЕ"; btn.disabled = false; btn.style.opacity = "1";
    if(best_bat) { document.getElementById("bat-selector").value = best_bat; saveSelection(); }
}

async function openServiceBat() { await eel.open_service_bat()(); }

eel.expose(update_service_status);
function update_service_status(isInstalled) {
    let span = document.getElementById("svc-status"); let btnToggle = document.getElementById("btn-toggle"); 
    if(isInstalled) {
        span.innerText = "РАБОТАЕТ"; span.style.color = "var(--accent-bg)";
        btnToggle.disabled = true; btnToggle.innerText = "БЛОКИРОВКА (СЛУЖБА)"; btnToggle.style.opacity = "0.5";
    } else {
        span.innerText = "НЕТ"; span.style.color = "var(--text-muted)";
        if(btnToggle.innerText === "БЛОКИРОВКА (СЛУЖБА)") {
            btnToggle.disabled = false; btnToggle.innerText = "ЗАПУСТИТЬ ОБХОД"; btnToggle.style.opacity = "1";
        }
    }
}

function saveAllSettings() {
    let data = { autostart: document.getElementById("set-autostart").checked, start_minimized: document.getElementById("set-minimized").checked };
    eel.save_settings(data)(); add_log("Настройки сохранены.");
}

async function selectFolder() {
    let folder = await eel.pick_folder()();
    if (folder) {
        if (await eel.update_zapret_path(folder)()) {
            document.getElementById("set-path").value = folder;
            document.getElementById("path-status").innerText = "Успешно!"; document.getElementById("path-status").style.color = "var(--accent-bg)";
            await reloadBatList();
        } else { document.getElementById("path-status").innerText = "Ошибка: Папка не найдена."; }
    }
}
async function resetFolder() {
    if (await eel.reset_zapret_path()()) {
        document.getElementById("set-path").value = ""; document.getElementById("path-status").innerText = "Сброшено."; document.getElementById("path-status").style.color = "var(--accent-bg)";
        await reloadBatList();
    }
}

// Логика переключения прозрачности рамки 
function toggleFrameMode() {
    let toggle = document.getElementById("set-transparent-frame");
    if (!toggle) return;
    
    let isTransparent = toggle.checked;
    let frameRow = document.getElementById("frame-color-row");
    
    // Скрываем или показываем выбор цвета рамки в зависимости от галочки
    if (isTransparent) {
        if(frameRow) frameRow.style.display = "none"; 
        syncFrameWithBackground();       
    } else {
        if(frameRow) frameRow.style.display = "flex"; 
        let colorPicker = document.getElementById("frame-color-picker");
        if(colorPicker) updateFrameColor(colorPicker.value, false); 
    }
    eel.save_settings({"transparent_frame": isTransparent})();
}

function syncFrameWithBackground() {
    let themeKey = document.getElementById("theme-selector").value;
    let bgColor = (themeKey === 'custom') ? document.getElementById("custom-bg-color-picker").value : THEMES[themeKey].bgMain;
    
    let metaTheme = document.getElementById("theme-meta");
    if(metaTheme) metaTheme.setAttribute("content", bgColor);
    eel.change_frame_color(bgColor)(); 
}

function updateFrameColor(hexColor, saveToConfig = true) {
    let toggle = document.getElementById("set-transparent-frame");
    if (toggle && toggle.checked) return; 

    let metaTheme = document.getElementById("theme-meta");
    if(metaTheme) metaTheme.setAttribute("content", hexColor);
    eel.change_frame_color(hexColor)();
    
    if(saveToConfig) eel.save_settings({"frame_color": hexColor})();
}

function setDynamicIconColor(hexColor, saveToConfig = true) {
    let img = new Image();
    img.src = "icon.png?" + new Date().getTime(); 
    img.onload = function() {
        let canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        let ctx = canvas.getContext("2d");
        
        ctx.drawImage(img, 0, 0);
        let imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        let data = imgData.data;
        
        let hex = hexColor.replace('#', '');
        let r = parseInt(hex.substring(0,2), 16); let g = parseInt(hex.substring(2,4), 16); let b = parseInt(hex.substring(4,6), 16);
        
        let hasTransparency = false;
        for (let i = 0; i < data.length; i += 4) { if (data[i+3] < 255) { hasTransparency = true; break; } }
        
        for (let i = 0; i < data.length; i += 4) {
            let finalAlpha;
            if (hasTransparency) {
                finalAlpha = data[i+3];
            } else {
                let brightness = (data[i] + data[i+1] + data[i+2]) / 3;
                finalAlpha = brightness < 128 ? (255 - brightness) : 0;
            }
            data[i] = r; data[i+1] = g; data[i+2] = b; data[i+3] = finalAlpha;
        }
        
        ctx.putImageData(imgData, 0, 0);
        document.getElementById("dynamic-favicon").href = canvas.toDataURL("image/png");
    };

    eel.change_tray_icon(hexColor)();
    if (saveToConfig) eel.save_settings({"tray_color": hexColor})();
}