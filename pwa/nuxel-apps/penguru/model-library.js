import {confirmDownload, formatBytes, sumBytes} from './download-confirm.js';

export function modelLibrary(container, call) {
  const jobs = new Map();
  let polling = false;
  const latest = {cards: [], enabled: false, perModel: {}};
  let bulk = null;
  let bulkPolling = false;
  const sizeLabel = value => formatBytes(value);

  function node(tag, text) {
    const result = document.createElement(tag);
    result.textContent = text;
    return result;
  }

  function allVariants(cards) {
    const out = [];
    for (const card of cards || []) {
      for (const variant of (card.variants || [])) out.push({card, variant});
    }
    return out;
  }

  function pendingVariants(cards) {
    return allVariants(cards).filter(({variant}) =>
      variant.download_allowed !== false && variant.status !== 'ready');
  }

  // The native downloader keeps a 256 MiB safety reserve. Read the same free
  // space the service will see so "download all" is not started when the
  // complete set cannot fit on this phone.
  const STORAGE_RESERVE = 256 * 1024 * 1024;
  function freeStorage() {
    try {
      const host = window.NuxelAndroid;
      if (!host || typeof host.deviceInfo !== 'function') return 0;
      const info = JSON.parse(host.deviceInfo() || '{}');
      return Math.max(0, Number(info.free_storage) || 0);
    } catch (error) {
      return 0;
    }
  }

  function renderBulkPanel(message) {
    const host = document.getElementById('models-bulk');
    if (!host) return;
    if (!latest.enabled) {
      host.replaceChildren();
      host.hidden = true;
      return;
    }
    host.hidden = false;
    // Keep the live progress panel stable while a bulk job is running.
    if (bulk && bulk.running) return;
    const entries = allVariants(latest.cards);
    if (!entries.length) {
      host.replaceChildren();
      return;
    }
    host.replaceChildren();
    const total = sumBytes(entries, item => item.variant.size_bytes);
    const todo = pendingVariants(latest.cards);
    const todoBytes = sumBytes(todo, item => item.variant.size_bytes);
    const free = freeStorage();
    const fits = !todo.length || !free || free >= todoBytes + STORAGE_RESERVE;
    const panel = node('article', '');
    panel.className = 'card bulk-panel';
    panel.append(node('h4', 'All required models'));
    panel.append(node('p', `Complete set: ${formatBytes(total)} across ${entries.length} model packages. `
      + (todo.length ? `${formatBytes(todoBytes)} remains to download.` : 'Everything is installed.')));
    if (free > 0) {
      panel.append(node('p', `Free storage on this phone: ${formatBytes(free)}`
        + (fits ? '.' : ` — not enough for this download (${formatBytes(todoBytes + STORAGE_RESERVE)} needed).`)));
    }
    const warning = node('p', 'Mobile-data warning: the complete set is several gigabytes. '
      + 'On mobile data this can use up your allowance and may cost money. Wi-Fi is strongly recommended.');
    warning.className = 'hint bulk-warning';
    panel.append(warning);
    if (message) {
      const status = node('p', message);
      status.setAttribute('role', 'status');
      panel.append(status);
    }
    if (todo.length) {
      const button = node('button', `Accept all & download remaining (${formatBytes(todoBytes)})`);
      button.type = 'button';
      button.className = 'primary';
      button.disabled = !fits;
      if (!fits) button.title = 'Not enough free storage for the complete model set';
      button.onclick = () => startBulk().catch(error => {
        const status = node('p', error.message || String(error));
        panel.append(status);
      });
      panel.append(button);
    }
    host.append(panel);
  }

  function showBulkProgress() {
    const host = document.getElementById('models-bulk');
    if (!host) return null;
    host.hidden = false;
    host.replaceChildren();
    const panel = node('article', '');
    panel.className = 'card bulk-panel';
    panel.append(node('h4', 'Downloading all required models'));
    const warning = node('p', 'Keep this phone on Wi-Fi if possible. The foreground service keeps '
      + 'downloading when the screen turns off.');
    warning.className = 'hint';
    const progress = document.createElement('progress');
    progress.max = 1;
    progress.value = 0;
    const status = node('p', 'Starting downloads…');
    status.setAttribute('role', 'status');
    const cancel = node('button', 'Cancel all downloads');
    cancel.type = 'button';
    cancel.onclick = async () => {
      cancel.disabled = true;
      status.textContent = 'Cancelling downloads…';
      for (const jobId of (bulk ? bulk.items.keys() : [])) {
        try { await call('cancel_download', {job_id: jobId}); } catch (error) { /* already stopped */ }
      }
    };
    panel.append(warning, progress, status, cancel);
    host.append(panel);
    return {progress, status, cancel};
  }

  function bulkTotals() {
    let doneBytes = 0;
    let ready = 0;
    let failed = bulk ? bulk.startFailures : 0;
    let active = 0;
    for (const entry of (bulk ? bulk.items.values() : [])) {
      if (entry.state === 'ready') {
        ready += 1;
        doneBytes += entry.size;
      } else if (['error', 'quarantined', 'cancelled'].includes(entry.state)) {
        failed += 1;
      } else {
        active += 1;
        doneBytes += entry.progress * entry.size;
      }
    }
    return {doneBytes, ready, failed, active,
      progress: bulk && bulk.total ? Math.min(1, doneBytes / bulk.total) : 0};
  }

  function updateBulkProgress() {
    if (!bulk || !bulk.ui) return;
    const totals = bulkTotals();
    bulk.ui.progress.value = totals.progress;
    bulk.ui.status.textContent = `${totals.ready} of ${bulk.totalCount} installed · `
      + `${Math.round(totals.progress * 100)}% · ${formatBytes(Math.max(0, bulk.total - totals.doneBytes))} left`
      + (totals.failed ? ` · ${totals.failed} failed` : '')
      + (totals.active ? ` · ${totals.active} active` : '');
  }

  async function finishBulk() {
    if (!bulk || !bulk.running) return;
    bulk.running = false;
    const totals = bulkTotals();
    const finished = `Download all finished: ${totals.ready} installed`
      + (totals.failed ? `, ${totals.failed} failed.` : '.');
    if (bulk.ui) {
      bulk.ui.progress.value = 1;
      bulk.ui.status.textContent = finished;
      bulk.ui.cancel.hidden = true;
    }
    try {
      const result = await call('list_models');
      latest.cards = result.models || latest.cards;
    } catch (error) { /* keep the cards we already have */ }
    bulk = null;
    render(latest.cards, latest.enabled, latest.perModel);
    renderBulkPanel(finished);
  }

  async function pollBulk() {
    if (!bulk || !bulk.running || bulkPolling) return;
    bulkPolling = true;
    try {
      let settled = true;
      for (const [jobId, entry] of bulk.items) {
        if (['ready', 'error', 'quarantined', 'cancelled'].includes(entry.state)) continue;
        try {
          const result = await call('download_status', {job_id: jobId});
          const job = result.job || {};
          entry.progress = Math.max(0, Math.min(1, Number(job.progress) || 0));
          if (['ready', 'error', 'quarantined', 'cancelled'].includes(job.state)) {
            entry.state = job.state;
            if (job.state === 'ready') entry.progress = 1;
          } else {
            settled = false;
          }
        } catch (error) {
          entry.state = 'error';
        }
      }
      updateBulkProgress();
      if (settled) await finishBulk();
    } finally {
      bulkPolling = false;
    }
  }

  async function startBulk() {
    if (bulk && bulk.running) return;
    const todo = pendingVariants(latest.cards);
    if (!todo.length) return;
    const todoBytes = sumBytes(todo, item => item.variant.size_bytes);
    const totalBytes = sumBytes(allVariants(latest.cards), item => item.variant.size_bytes);
    const free = freeStorage();
    if (free > 0 && free < todoBytes + STORAGE_RESERVE) {
      renderBulkPanel(`Not enough free storage for the complete download: `
        + `${formatBytes(todoBytes + STORAGE_RESERVE)} needed, ${formatBytes(free)} free. `
        + 'Free space or download packages individually.');
      return;
    }
    const accepted = await confirmDownload({
      title: 'Download all required PenGuru models?',
      sizeBytes: todoBytes,
      packageCount: todo.length,
      detail: `The complete model set is ${formatBytes(totalBytes)}. `
        + (free > 0 ? `Free storage on this phone: ${formatBytes(free)}. ` : '')
        + 'This installs every model package in the library in one go.',
    });
    if (!accepted) return;
    const ui = showBulkProgress();
    bulk = {
      running: true,
      total: todoBytes,
      totalCount: todo.length,
      startFailures: 0,
      items: new Map(),
      ui,
    };
    for (const {card, variant} of todo) {
      try {
        const result = await call('start_download', {
          model_id: card.model_id,
          variant_id: variant.variant_id,
          license_accepted: true,
          license_revision: variant.source_revision,
        });
        bulk.items.set(result.job_id, {
          card, variant,
          size: Number(variant.size_bytes) || 0,
          state: 'downloading',
          progress: 0,
        });
      } catch (error) {
        bulk.startFailures += 1;
        if (bulk.ui) bulk.ui.status.textContent = 'Could not start '
          + card.model_id + '/' + variant.variant_id + ': ' + error.message;
      }
    }
    updateBulkProgress();
    if (!bulk.items.size) await finishBulk();
  }

  function render(cards, enabled, perModel = {}) {
    latest.cards = cards || [];
    latest.enabled = !!enabled;
    latest.perModel = perModel || {};
    renderBulkPanel();
    if (enabled && jobs.size) return;
    jobs.clear();
    container.replaceChildren();
    if (!enabled) {
      container.textContent = 'Enable PenGuru to inspect and download packages. No model downloads run while OFF.';
      return;
    }
    if (!latest.cards.length) {
      container.textContent = 'No model packages are available.';
      return;
    }
    for (const card of latest.cards) {
      const article = node('article', '');
      article.className = 'card';
      article.append(node('h4', card.name || card.model_id), node('p', 'Model id: ' + card.model_id));
      if (!card.variants.length) article.append(node('p', 'No approved package is available.'));
      for (const variant of card.variants) {
        article.append(node('p', `${variant.format} · ${variant.quantization} · ${sizeLabel(variant.size_bytes)} · ${variant.engine}`));
        const source = node('a', variant.source_repo);
        const sourceUrl = variant.source_url && /github\.com|raw\.githubusercontent\.com/.test(variant.source_url)
          ? variant.source_url
          : 'https://huggingface.co/' + variant.source_repo + '/tree/' + variant.source_revision;
        source.href = sourceUrl;
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        source.onclick = event => {
          const host = window.NuxelAndroid;
          if (host && typeof host.openExternal === 'function') {
            event.preventDefault();
            host.openExternal(sourceUrl);
          }
        };
        article.append(source, node('p', `Revision: ${variant.source_revision}`));
        const details = node('details', '');
        details.append(node('summary', 'Hashes, license and provenance'),
          node('pre', JSON.stringify(variant.files, null, 2)),
          node('p', `${variant.license.spdx}: ${variant.license.notice || ''}`));
        article.append(details, node('p', `${variant.status}: ${variant.detail}`),
          node('p', variant.download_reason || 'Manifest trust not verified'));
        if (variant.installed_path) article.append(node('p', 'Installed at: ' + variant.installed_path));
        const accepted = document.createElement('input');
        accepted.type = 'checkbox';
        accepted.disabled = !variant.download_allowed || variant.status === 'ready';
        const label = node('label', '');
        label.append(accepted, document.createTextNode(' I reviewed this revision’s license and provenance.'));
        const download = node('button', variant.status === 'ready' ? 'Downloaded · ready' : 'Download to this phone');
        let active = false;
        const updateDownload = () => {
          download.disabled = active || !accepted.checked || !variant.download_allowed || variant.status === 'ready';
        };
        download.disabled = true;
        accepted.onchange = updateDownload;
        const progress = document.createElement('progress');
        progress.max = 1;
        progress.value = 0;
        progress.hidden = true;
        const status = node('p', '');
        status.setAttribute('role', 'status');
        const cancel = node('button', 'Cancel download');
        cancel.hidden = true;
        download.onclick = async () => {
          if (download.disabled) return;
          download.disabled = true;
          const confirmed = await confirmDownload({
            title: `Download ${card.name || card.model_id}?`,
            sizeBytes: variant.size_bytes,
            packageCount: 1,
            detail: `Model package ${card.model_id}/${variant.variant_id}.`,
          });
          if (!confirmed) {
            updateDownload();
            return;
          }
          active = true;
          accepted.disabled = true;
          updateDownload();
          try {
            const result = await call('start_download', {model_id: card.model_id,
              variant_id: variant.variant_id, license_accepted: accepted.checked,
              license_revision: variant.source_revision});
            progress.hidden = cancel.hidden = false;
            jobs.set(result.job_id, {progress, status, cancel, finish: state => {
              active = false;
              accepted.disabled = !variant.download_allowed;
              if (state === 'ready') {
                variant.status = 'ready';
                download.textContent = 'Downloaded · ready';
                remove.disabled = false;
                accepted.disabled = true;
              }
              updateDownload();
              renderBulkPanel();
            }});
            cancel.onclick = () => call('cancel_download', {job_id: result.job_id}).catch(error => { status.textContent = error.message; });
          } catch (error) {
            status.textContent = error.message;
            active = false;
            accepted.disabled = !variant.download_allowed;
            updateDownload();
          }
        };
        const remove = node('button', 'Delete from this phone');
        remove.disabled = variant.status !== 'ready';
        remove.onclick = async () => {
          if (active || jobs.size || (bulk && bulk.running)) {
            status.textContent = 'Finish or cancel the download first.';
            return;
          }
          if (!confirm(`Delete ${card.model_id} ${variant.variant_id} from this phone?`)) return;
          remove.disabled = true;
          try {
            await call('delete_model', {model_id: card.model_id, variant_id: variant.variant_id});
            variant.status = 'not_installed';
            render((await call('list_models')).models, latest.enabled, latest.perModel);
          } catch (error) { status.textContent = error.message; remove.disabled = false; }
        };
        const override = node('select', '');
        override.setAttribute('aria-label', card.model_id + ' runtime override');
        for (const [value, title] of [['inherit', 'Inherit global runtime'], ['llama.cpp', 'llama.cpp'], ['onnxruntime-genai', 'ORT GenAI (requires ONNX package)']]) {
          const option = node('option', title); option.value = value; override.append(option);
        }
        override.value = perModel[card.model_id] || 'inherit';
        override.onchange = async () => {
          try {
            await call('set_runtime', {model_id: card.model_id, engine: override.value});
            latest.perModel[card.model_id] = override.value;
          } catch (error) { status.textContent = error.message; override.value = latest.perModel[card.model_id] || 'inherit'; }
        };
        article.append(label, download, remove, cancel, progress, status);
        if (card.model_id !== 'sonarbird'
            && !['voice_activity', 'noise_suppression', 'talkback_voice', 'speech_recognition'].includes(card.role)
            && !card.variants.some(item => String(item.engine || '').includes('tts'))) article.append(override);
      }
      container.append(article);
    }
  }

  setInterval(async () => {
    if (polling || (!jobs.size && !(bulk && bulk.running))) return;
    polling = true;
    try {
      for (const [id, view] of jobs) {
        const job = (await call('download_status', {job_id: id})).job;
        view.progress.value = job.progress;
        view.status.textContent = `${job.state} · ${Math.round(job.progress * 100)}% · ${job.detail || ''}`;
        if (['ready', 'error', 'quarantined', 'cancelled'].includes(job.state)) {
          jobs.delete(id);
          view.cancel.hidden = true;
          view.finish(job.state);
        }
      }
      await pollBulk();
    } catch (error) {
      for (const view of jobs.values()) view.status.textContent = error.message;
    } finally { polling = false; }
  }, 1500);

  return {render};
}
