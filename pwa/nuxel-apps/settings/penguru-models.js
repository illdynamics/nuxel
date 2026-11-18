export function modelLibrary(container, call) {
  const jobs = new Map();
  let polling = false;
  function node(tag, text) {
    const result = document.createElement(tag);
    result.textContent = text;
    return result;
  }
  function render(cards, enabled, perModel = {}) {
    if (enabled && jobs.size) return;
    jobs.clear();
    container.replaceChildren();
    if (!enabled) {
      container.textContent = 'Enable PenGuru to inspect and download packages. No model downloads run while OFF.';
      return;
    }
    for (const card of cards) {
      const article = node('article', '');
      article.className = 'card';
      article.append(node('h4', card.name || card.model_id));
      if (!card.variants.length) article.append(node('p', 'No approved package. Squad currently uses deterministic routing only.'));
      for (const variant of card.variants) {
        article.append(node('p', `${variant.format} · ${variant.quantization} · ${(variant.size_bytes / 1e9).toFixed(2)} GB · ${variant.engine}`));
        const source = node('a', variant.source_repo);
        source.href = 'https://huggingface.co/' + variant.source_repo + '/tree/' + variant.source_revision;
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        article.append(source, node('p', `Revision: ${variant.source_revision}`));
        const details = node('details', '');
        details.append(node('summary', 'Hashes, license and provenance'),
          node('pre', JSON.stringify(variant.files, null, 2)),
          node('p', `${variant.license.spdx}: ${variant.license.notice || ''}`));
        article.append(details, node('p', `${variant.status}: ${variant.detail}`),
          node('p', variant.download_reason || 'Manifest trust not verified'));
        const accepted = document.createElement('input');
        accepted.type = 'checkbox';
        accepted.disabled = !variant.download_allowed;
        const label = node('label', '');
        label.append(accepted, document.createTextNode(' I reviewed this revision’s license and provenance.'));
        const download = node('button', variant.status === 'ready' ? 'Verified & ready' : 'Download from Hugging Face');
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
                download.textContent = 'Verified & ready';
                remove.disabled = false;
              }
              updateDownload();
            }});
            cancel.onclick = () => call('cancel_download', {job_id: result.job_id}).catch(error => { status.textContent = error.message; });
          } catch (error) {
            status.textContent = error.message;
            active = false;
            accepted.disabled = !variant.download_allowed;
            updateDownload();
          }
        };
        const remove = node('button', 'Delete package');
        remove.disabled = variant.status === 'not_installed';
        remove.onclick = async () => {
          if (active || jobs.size) { status.textContent = 'Finish or cancel the download first.'; return; }
          if (!confirm(`Delete ${card.model_id} ${variant.variant_id} from this device?`)) return;
          remove.disabled = true;
          try {
            await call('delete_model', {model_id: card.model_id, variant_id: variant.variant_id});
            render((await call('list_models')).models, true, perModel);
          } catch (error) { status.textContent = error.message; remove.disabled = false; }
        };
        const override = node('select', '');
        override.setAttribute('aria-label', card.model_id + ' runtime override');
        for (const [value, title] of [['inherit', 'Inherit global runtime'], ['llama.cpp', 'llama.cpp'], ['onnxruntime-genai', 'ORT GenAI (requires ONNX package)']]) {
          const option = node('option', title); option.value = value; if(value==='onnxruntime-genai') option.disabled=true; override.append(option);
        }
        override.value = perModel[card.model_id] || 'inherit';
        override.onchange = async () => {
          try {
            await call('set_runtime', {model_id: card.model_id, engine: override.value});
            perModel[card.model_id] = override.value;
          } catch (error) { status.textContent = error.message; override.value = perModel[card.model_id] || 'inherit'; }
        };
        article.append(label, download, remove, cancel, progress, status);
        if (card.model_id !== 'sonarbird') article.append(override);
      }
      container.append(article);
    }
  }
  setInterval(async () => {
    if (polling || !jobs.size) return;
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
    } catch (error) {
      for (const view of jobs.values()) view.status.textContent = error.message;
    } finally { polling = false; }
  }, 1500);
  return {render};
}
