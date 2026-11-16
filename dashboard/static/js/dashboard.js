const API_BASE = '';

if (window.Chart) {
    Chart.defaults.color = '#667173';
    Chart.defaults.borderColor = '#cfd0ca';
}

function el(id) { return document.getElementById(id); }

async function fetchAPI(endpoint) {
    try {
        const r = await fetch('' + endpoint);
        const d = await r.json();
        if (d.status === 'success') return d.data;
        throw new Error(d.message || 'API error');
    } catch (e) {
        showToast('API error (API 오류) (' + endpoint + '): ' + e.message, 'error');
        return null;
    }
}

function showToast(msg, type) {
    var t = el('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast toast-' + (type || 'info');
    requestAnimationFrame(function() { t.classList.add('show'); });
    clearTimeout(t._hideTimer);
    t._hideTimer = setTimeout(function() { t.classList.remove('show'); }, 5000);
}

var chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

function setUpdateTime(id) {
    var e = el(id);
    if (e) e.textContent = 'Update (업데이트): ' + new Date().toLocaleTimeString();
}

function toggleSidebar() {
    var s = el('sidebar'), o = el('sidebar-overlay');
    if (s) s.classList.toggle('open');
    if (o) o.classList.toggle('show');
}

function closeSidebar() {
    var s = el('sidebar'), o = el('sidebar-overlay');
    if (s) s.classList.remove('open');
    if (o) o.classList.remove('show');
}

function showSection(id, ev) {
    if (ev) ev.preventDefault();
    document.querySelectorAll('.section').forEach(function(s) { s.style.display = 'none'; });
    document.querySelectorAll('.sidebar-nav a').forEach(function(a) { a.classList.remove('active'); });
    var sec = el('section-' + id);
    if (sec) sec.style.display = 'block';
    if (ev && ev.currentTarget) ev.currentTarget.classList.add('active');
    closeSidebar();
    if (id === 'overview') loadOverview();
    if (id === 'equipment') loadEquipment();
    if (id === 'analysis') loadAnalysis();
    if (id === 'anomalies') loadAnomalies();
    if (id === 'drift') loadDrift();
    if (id === 'history') loadHistory();
    if (id === 'rul') loadRUL();
    if (id === 'visualizations') loadVisualizations();
}

function setText(id, txt) { var e = el(id); if (e) e.textContent = txt; }

function statusBadge(s) {
    var m = { '양호': 'badge-success', '주의': 'badge-warning', '경고': 'badge-danger', '위험': 'badge-danger' };
    return '<span class="badge ' + (m[s] || 'badge-warning') + '">' + s + '</span>';
}

function driftBadge(drifted) {
    return drifted ? '<span class="badge badge-danger">[!] Drift</span>' : '<span class="badge badge-success">[.] OK</span>';
}

// === Overview ===

async function loadOverview() {
    var s = await fetchAPI('/api/v1/summary');
    if (s) {
        setText('stat-total', s.total_records.toLocaleString());
        setText('stat-defect', s.defect_rate.toFixed(2) + '%');
        setText('hero-defect', s.defect_rate.toFixed(2));
        setText('stat-temp', s.avg_temperature.toFixed(1) + '\u00B0C');
        setText('stat-pressure', s.avg_pressure.toFixed(1) + ' bar');
        setText('stat-humidity', (s.avg_humidity || 0).toFixed(1) + '%');
        setText('stat-cycle', (s.avg_cycle_time || 0).toFixed(1) + 's');
        setUpdateTime('update-time-overview');
    }
    var t = await fetchAPI('/api/v1/trends');
    if (t) createHourlyChart(t);
    var l = await fetchAPI('/api/v1/lines');
    if (l) createLinesChart(l);
    loadLatestModelMetrics();
}

async function loadLatestModelMetrics() {
    var latest = await fetchAPI('/api/v1/history/models/latest/metrics');
    if (!latest || !latest.metrics) return;
    var f1 = latest.metrics.f1_1;
    var prAuc = latest.metrics.auc_pr;
    var labels = document.querySelectorAll('.proof-strip b');
    if (labels[1] && f1 !== undefined && prAuc !== undefined) {
        labels[1].textContent = 'Test F1 ' + Number(f1).toFixed(4) + ' · PR-AUC ' + Number(prAuc).toFixed(4);
        labels[1].title = latest.model_name + ' ' + latest.version + ' · threshold ' + Number(latest.threshold).toFixed(4);
    }
}

function createHourlyChart(t) {
    destroyChart('chart-hourly');
    var c = el('chart-hourly');
    if (!c) return;
    var ctx = c.getContext('2d');
    chartInstances['chart-hourly'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: t.hours.map(function(h) { return h + '\uC2DC'; }),
            datasets: [{ label: 'Defect Rate (%) (\uBD88\uB7C9\uB960)', data: t.defect_rates, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', fill: true, tension: 0.4 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, title: { display: true, text: 'Defect Rate (%) (\uBD88\uB7C9\uB960)' } } } }
    });
}

function createLinesChart(l) {
    destroyChart('chart-lines');
    var c = el('chart-lines');
    if (!c) return;
    var ctx = c.getContext('2d');
    chartInstances['chart-lines'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: l.map(function(x) { return x.line; }),
            datasets: [{ label: 'Defect Rate (%) (\uBD88\uB7C9\uB960)', data: l.map(function(x) { return x.defect_rate; }), backgroundColor: ['#4f46e5', '#10b981', '#f59e0b'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, title: { display: true, text: 'Defect Rate (%) (\uBD88\uB7C9\uB960)' } } } }
    });
}

// === Persisted SQL history (separate from the live synthetic drift view) ===
async function loadHistory() {
    var results = await Promise.all([
        fetchAPI('/api/v1/history/quality'),
        fetchAPI('/api/v1/history/models?limit=10'),
        fetchAPI('/api/v1/history/drift/latest'),
        fetchAPI('/api/v1/history/predictions')
    ]);
    var quality = results[0] || [], models = results[1] || [], drift = results[2], predictions = results[3] || [];
    var stats = el('history-stats');
    if (stats) stats.innerHTML = '<div class="stat-card"><div class="label">SQL 품질 집계 행</div><div class="value">' + quality.length + '</div></div><div class="stat-card"><div class="label">TEST 예측 건수</div><div class="value">' + predictions.reduce(function(sum, row) { return sum + row.prediction_count; }, 0) + '</div></div><div class="stat-card"><div class="label">예측 불량 건수</div><div class="value">' + predictions.reduce(function(sum, row) { return sum + row.predicted_defect_count; }, 0) + '</div></div><div class="stat-card"><div class="label">등록 모델 버전</div><div class="value">' + models.length + '</div></div><div class="stat-card"><div class="label">최근 드리프트</div><div class="value">' + (drift ? (drift.drift_detected ? '[DRIFT]' : '[OK]') : '이력 없음') + '</div></div>';
    createHistoryQualityChart(quality);
    createHistoryPredictionChart(predictions);
    var detail = el('history-drift-detail');
    if (detail) detail.textContent = drift ? (drift.created_at + ' · ' + (drift.drift_detected ? '드리프트 감지' : '정상') + ' · live: ' + drift.live_source) : '저장된 실행 이력이 없습니다.';
    var table = el('history-model-table');
    if (table) table.innerHTML = models.length ? models.map(function(m) {
        return '<tr><td>' + m.model_name + '</td><td>' + m.version + '</td><td>' + m.trained_at + '</td><td>' + (m.threshold === null ? '-' : Number(m.threshold).toFixed(2)) + '</td><td><code>' + m.artifact_sha256.slice(0, 12) + '…</code></td></tr>';
    }).join('') : '<tr><td colspan="5">저장된 모델 이력이 없습니다. `python main.py`를 실행하면 기록됩니다.</td></tr>';
    setUpdateTime('update-time-history');
}

function createHistoryPredictionChart(rows) {
    destroyChart('chart-history-predictions');
    var c = el('chart-history-predictions');
    if (!c) return;
    chartInstances['chart-history-predictions'] = new Chart(c.getContext('2d'), { type: 'bar', data: { labels: rows.map(function(r) { return r.date + ' · ' + r.production_line; }), datasets: [{ label: 'Predicted defects (held-out test)', data: rows.map(function(r) { return r.predicted_defect_count; }), backgroundColor: '#ff5b36' }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#f0eee7' } } }, scales: { x: { ticks: { color: '#b8c5c1' }, grid: { color: '#ffffff22' } }, y: { beginAtZero: true, ticks: { color: '#b8c5c1' }, grid: { color: '#ffffff22' } } } } });
}

function createHistoryQualityChart(rows) {
    destroyChart('chart-history-quality');
    var c = el('chart-history-quality');
    if (!c) return;
    var labels = rows.map(function(r) { return r.date + ' · ' + r.production_line; });
    chartInstances['chart-history-quality'] = new Chart(c.getContext('2d'), { type: 'bar', data: { labels: labels, datasets: [{ label: 'Actual defect rate (%)', data: rows.map(function(r) { return r.defect_rate; }), backgroundColor: '#4f46e5' }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } } });
}

// === Equipment ===

async function loadEquipment() {
    var ct = el('equipment-table-container'), ld = el('loading-equipment');
    if (ld) ld.style.display = 'flex';
    if (ct) ct.style.display = 'none';
    var eq = await fetchAPI('/api/v1/equipment');
    if (ld) ld.style.display = 'none';
    if (!eq) return;
    if (ct) ct.style.display = 'block';
    var tb = el('equipment-table');
    if (!tb) return;
    tb.innerHTML = eq.map(function(x) {
        var a = x.alerts && x.alerts.length ? x.alerts.join(', ') : '-';
        return '<tr><td><strong>' + x.equipment_id + '</strong></td><td>' + x.health_score + '/100</td><td>' + statusBadge(x.status) + '</td><td>' + a + '</td></tr>';
    }).join('');
    setUpdateTime('update-time-equipment');
}

// === Analysis ===

async function loadAnalysis() {
    var corr = await fetchAPI('/api/v1/correlation');
    if (corr) createHeatmap(corr);
    var sc = await fetchAPI('/api/v1/scatter');
    if (sc) createScatter(sc);
    setUpdateTime('update-time-analysis');
}

function createHeatmap(d) {
    var container = el('heatmap-container');
    if (!container) return;
    var cols = d.columns, n = cols.length, matrix = d.matrix;
    var absMax = 0;
    for (var i = 0; i < n; i++) for (var j = 0; j < n; j++) { var v = Math.abs(matrix[i][j]); if (v > absMax) absMax = v; }
    if (absMax === 0) absMax = 1;

    var h =
        '<div class="heatmap-grid" style="grid-template-columns: 100px repeat(' + n + ', 1fr);">' +
        '<div class="heatmap-cel label"></div>';
    for (var j = 0; j < n; j++) h += '<div class="heatmap-cel header">' + cols[j] + '</div>';
    for (var i = 0; i < n; i++) {
        h += '<div class="heatmap-cel header">' + cols[i] + '</div>';
        for (var j = 0; j < n; j++) {
            var v = matrix[i][j], a = Math.abs(v) / absMax;
            var r, g, b;
            if (v > 0) { r = 239; g = Math.round(68 + (187 * (1 - a))); b = Math.round(68 + (187 * (1 - a))); }
            else { r = Math.round(59 + (180 * (1 - a))); g = Math.round(130 + (125 * (1 - a))); b = 246; }
            var cell = '<div class="heatmap-cel val" style="background:rgba(' + r + ',' + g + ',' + b + ',' + (0.3 + 0.7 * a) + ');" title="' + cols[i] + ' × ' + cols[j] + ': ' + v.toFixed(3) + '">';
            if (i === j) cell += '<strong>' + v.toFixed(2) + '</strong>';
            else cell += v.toFixed(2);
            cell += '</div>';
            h += cell;
        }
    }
    h += '</div>';
    container.innerHTML = h;
}

function createScatter(d) {
    destroyChart('chart-scatter');
    var c = el('chart-scatter');
    if (!c) return;
    var ctx = c.getContext('2d');
    chartInstances['chart-scatter'] = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                { label: 'Normal (\uC815\uC0C1)', data: d.normal, backgroundColor: 'rgba(16,185,129,0.6)' },
                { label: 'Anomaly (\uC774\uC0C1)', data: d.anomaly, backgroundColor: 'rgba(239,68,68,0.6)' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { title: { display: true, text: 'Temperature (C) (\uC628\uB3C4)' } }, y: { title: { display: true, text: 'Vibration (\uC9C4\uB3D9)' } } } }
    });
}

// === Anomalies ===

async function loadAnomalies() {
    var ld = el('loading-anomalies');
    if (ld) ld.style.display = 'flex';
    var d = await fetchAPI('/api/v1/anomalies');
    if (ld) ld.style.display = 'none';
    if (!d) return;
    var se = el('anomaly-stats');
    if (se) se.innerHTML = '<div class="stat-card"><div class="label">Total (\uC804\uCCB4)</div><div class="value">' + d.summary.total_records.toLocaleString() + '</div></div><div class="stat-card"><div class="label">Anomalies (\uC774\uC0C1\uCE58)</div><div class="value" style="color:var(--danger)">' + d.summary.anomaly_count + '</div></div><div class="stat-card"><div class="label">Rate (\uBE44\uC728)</div><div class="value">' + d.summary.anomaly_rate.toFixed(2) + '%</div></div>';
    var tb = el('anomaly-table');
    if (!tb) return;
    tb.innerHTML = d.top_anomalies.map(function(a) {
        return '<tr><td>' + (a.production_line || '-') + '</td><td>' + (a.temperature ? a.temperature.toFixed(1) : '-') + ' \u00B0C</td><td>' + (a.pressure ? a.pressure.toFixed(1) : '-') + ' bar</td><td>' + (a.vibration ? a.vibration.toFixed(4) : '-') + '</td><td>' + (a.anomaly_score ? a.anomaly_score.toFixed(4) : '-') + '</td></tr>';
    }).join('');
    setUpdateTime('update-time-anomalies');
}

// === Drift ===

async function loadDrift() {
    var ld = el('loading-drift');
    if (ld) ld.style.display = 'flex';
    var d = await fetchAPI('/api/v1/drift');
    if (ld) ld.style.display = 'none';
    if (!d) return;

    if (d.source_mode === 'simulated') {
        showToast(d.source_note || '합성 드리프트 시나리오입니다.', 'info');
    }

    var totalDrifted = d.drifted_features.filter(function(f) { return f.drifted; }).length;
    var statsEl = el('drift-stats');
    if (statsEl) statsEl.innerHTML =
        '<div class="stat-card"><div class="label">\uCD1D \uD2B9\uC131</div><div class="value">' + d.drifted_features.length + '</div></div>' +
        '<div class="stat-card"><div class="label">\uB4DC\uB9AC\uD504\uD2B8 \uAC10\uC9C0</div><div class="value" style="color:' + (totalDrifted > 0 ? 'var(--danger)' : 'var(--success)') + '">' + totalDrifted + '</div></div>' +
        '<div class="stat-card"><div class="label">\uC0C1\uD0DC</div><div class="value">' + (d.drift_detected ? '[DRIFT]' : '[OK]') + '</div></div>';
    setUpdateTime('update-time-drift');

    var tb = el('drift-table');
    if (!tb) return;
    tb.innerHTML = d.drifted_features.map(function(f) {
        var ksP = f.ks_p_value !== undefined ? f.ks_p_value.toFixed(4) : '-';
        var psi = f.psi !== undefined ? f.psi.toFixed(4) : '-';
        return '<tr>' +
            '<td><strong>' + f.feature + '</strong></td>' +
            '<td>' + ksP + '</td>' +
            '<td>' + driftBadge(f.ks_drifted) + '</td>' +
            '<td>' + psi + '</td>' +
            '<td>' + driftBadge(f.psi_drifted) + '</td>' +
            '<td>' + driftBadge(f.drifted) + '</td>' +
            '</tr>';
    }).join('');
}

// === RUL ===

async function loadRUL() {
    var ld = el('loading-rul');
    if (ld) ld.style.display = 'flex';
    var eq = await fetchAPI('/api/v1/rul');
    if (ld) ld.style.display = 'none';
    if (!eq) return;
    var tb = el('rul-table');
    if (!tb) return;
    tb.innerHTML = eq.map(function(x) {
        return '<tr><td><strong>' + x.equipment_id + '</strong><br><small>' + (x.name || '') + '</small></td><td>' + x.health_score + '/100 ' + statusBadge(x.status) + '</td><td>' + (x.reliability_score || 0).toFixed(1) + '/100</td><td>' + (x.remaining_hours || 0).toFixed(0) + '</td><td>' + (x.recommended_maintenance_date || '-') + '</td><td>' + ((x.confidence || 0) * 100).toFixed(0) + '%</td></tr>';
    }).join('');
    setUpdateTime('update-time-rul');
}

// === Visualizations ===

async function loadVisualizations() {
    var ld = el('loading-visualizations');
    if (ld) ld.style.display = 'flex';
    var f = await fetchAPI('/api/v1/visualizations');
    if (ld) ld.style.display = 'none';
    if (!f) return;
    var g = el('visualization-gallery');
    if (!g) return;
    g.innerHTML = f.map(function(n) {
        return '<div class="chart-card"><h3>' + n.replace('.png','').replace(/_/g,' ') + '</h3><img src="/visualizations/' + n + '" alt="' + n + '" style="width:100%;height:auto;border-radius:8px" loading="lazy"></div>';
    }).join('');
    setUpdateTime('update-time-visualizations');
}

function applyPortfolioLabels() {
    var eyebrow = document.querySelector('.overview-hero .eyebrow');
    if (eyebrow) eyebrow.innerHTML = '<span></span> SMART MANUFACTURING · PORTFOLIO DEMO';
    var copy = document.querySelector('.overview-hero .hero-copy');
    if (copy) copy.innerHTML = '합성 제조 센서 데이터를 기반으로 품질 위험, 이상 패턴, 모델 이력을 하나의 <strong>로컬 포트폴리오 화면</strong>에서 확인합니다.';
    var live = document.querySelector('.machine-card .live');
    if (live) live.innerHTML = '<b></b> LOCAL SNAPSHOT';
    var labels = ['Chronological train / val / test', 'Loading latest test metrics…', 'KS test + PSI', 'SYNTHETIC DATA'];
    document.querySelectorAll('.proof-strip b').forEach(function(node, index) {
        if (labels[index]) node.textContent = labels[index];
    });
    var hero = document.querySelector('.overview-hero > div:first-child');
    if (hero && !el('portfolio-disclaimer')) {
        var note = document.createElement('p');
        note.id = 'portfolio-disclaimer';
        note.className = 'hero-disclaimer';
        note.innerHTML = '<span>NOTE</span> 실제 생산 라인·실시간 운영 성능을 의미하지 않습니다.';
        hero.appendChild(note);
    }
}

document.addEventListener('DOMContentLoaded', function() { applyPortfolioLabels(); loadOverview(); });
