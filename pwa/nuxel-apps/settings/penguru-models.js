export function modelLibrary(container, call) {
  const jobs = new Map();
  let polling = false;
  function node(tag, text) {
    const result = document.createElement(tag);
    result.textContent = text;
    return result;
  }
  function render(cards, enabled) {
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
        source.href = 'https://huggingface.co/' + variant.source_repo;
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
        download.disabled = true;
        accepted.onchange = () => { download.disabled = !accepted.checked || !variant.download_allowed || variant.status === 'ready'; };
        const progress = document.createElement('progress');
        progress.max = 1;
        progress.value = 0;
        progress.hidden = true;
        const status = node('p', '');
        status.setAttribute('role', 'status');
        const cancel = node('button', 'Cancel download');
        cancel.hidden = true;
        download.onclick = async () => {
          download.disabled = true;
          try {
            const result = await call('start_download', {model_id: card.model_id,
              variant_id: variant.variant_id, license_accepted: accepted.checked,
              license_revision: variant.source_revision});
            progress.hidden = cancel.hidden = false;
            jobs.set(result.job_id, {progress, status, cancel, download});
            cancel.onclick = () => call('cancel_download', {job_id: result.job_id}).catch(error => { status.textContent = error.message; });
          } catch (error) {
            status.textContent = error.message;
            download.disabled = !variant.download_allowed;
          }
        };
        article.append(label, download, cancel, progress, status);
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
          view.download.disabled = job.state === 'ready';
        }
      }
    } catch (error) {
      for (const view of jobs.values()) view.status.textContent = error.message;
    } finally { polling = false; }
  }, 1500);
  return {render};
}
