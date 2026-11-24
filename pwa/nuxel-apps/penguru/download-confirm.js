// Shared confirmation dialog for large downloads.
//
// A single model or runtime can be hundreds of megabytes; the complete model
// set is several gigabytes. Android does not tell a WebView whether the active
// connection is metered, so warn before every download and state the exact
// total that will be transferred.

export function formatBytes(value) {
  const n = Math.max(0, Number(value) || 0);
  if (n >= 1e9) return (n / 1e9).toFixed(2) + ' GB';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' MB';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + ' KB';
  return n + ' B';
}

export function sumBytes(items, pick) {
  const get = typeof pick === 'function' ? pick : (item => item);
  return (items || []).reduce((total, item) => total + (Number(get(item)) || 0), 0);
}

/**
 * Show a blocking mobile-data warning. Resolves true only after the owner
 * explicitly presses the download button.
 */
export function confirmDownload(options) {
  options = options || {};
  const sizeBytes = Math.max(0, Number(options.sizeBytes) || 0);
  const count = Math.max(0, Number(options.packageCount) || 0);
  const title = options.title || 'Confirm download';
  const confirmLabel = options.confirmLabel || (sizeBytes > 0
    ? 'Download ' + formatBytes(sizeBytes) : 'Download');
  const countText = count > 1 ? ' across ' + count + ' packages' : '';
  const detail = options.detail || '';

  return new Promise(resolve => {
    // Only one warning may be open at a time.
    const previous = document.querySelector('.download-warning-backdrop');
    if (previous) previous.dispatchEvent(new Event('download-warning-dismiss'));

    const overlay = document.createElement('div');
    overlay.className = 'download-warning-backdrop';
    overlay.setAttribute('role', 'presentation');

    const dialog = document.createElement('div');
    dialog.className = 'download-warning';
    dialog.setAttribute('role', 'alertdialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'download-warning-title');
    dialog.setAttribute('aria-describedby', 'download-warning-body');

    const heading = document.createElement('h3');
    heading.id = 'download-warning-title';
    heading.textContent = title;

    const warning = document.createElement('p');
    warning.className = 'download-warning-lead';
    warning.textContent = 'Mobile-data warning';

    const body = document.createElement('p');
    body.id = 'download-warning-body';
    const sizeSentence = sizeBytes > 0
      ? 'This download is ' + formatBytes(sizeBytes) + countText + '. '
      : 'This download can be large. ';
    body.textContent = sizeSentence
      + (sizeBytes >= 1e9
        ? 'On mobile data a download like this can easily be several gigabytes, '
          + 'use up your data allowance and cost money. '
        : 'On mobile data, larger model sets can reach several gigabytes in total; '
          + 'every package uses your data allowance and may cost money. ')
      + 'Wi-Fi is strongly recommended.';

    const sizeLine = document.createElement('p');
    sizeLine.className = 'download-warning-size';
    sizeLine.textContent = sizeBytes > 0
      ? 'Total transfer: ' + formatBytes(sizeBytes)
        + (sizeBytes >= 1e9 ? ' (~' + (sizeBytes / 1e9).toFixed(1) + ' gigabytes)' : '')
      : 'Total size: unknown';

    const extra = detail ? document.createElement('p') : null;
    if (extra) {
      extra.className = 'hint';
      extra.textContent = detail;
    }

    const actions = document.createElement('div');
    actions.className = 'controls';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.textContent = 'Cancel';
    const confirm = document.createElement('button');
    confirm.type = 'button';
    confirm.className = 'primary';
    confirm.textContent = confirmLabel;
    actions.append(cancel, confirm);

    dialog.append(heading, warning, body, sizeLine);
    if (extra) dialog.append(extra);
    dialog.append(actions);
    overlay.append(dialog);

    let settled = false;
    function close(result) {
      if (settled) return;
      settled = true;
      document.removeEventListener('keydown', onKey, true);
      overlay.removeEventListener('download-warning-dismiss', dismiss);
      overlay.remove();
      resolve(!!result);
    }
    function dismiss() { close(false); }
    function onKey(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        close(false);
      } else if (event.key === 'Tab') {
        // Keep focus inside the confirmation while it is open.
        const focusable = [cancel, confirm];
        const index = focusable.indexOf(document.activeElement);
        event.preventDefault();
        const next = event.shiftKey
          ? (index <= 0 ? focusable[focusable.length - 1] : focusable[index - 1])
          : (index === focusable.length - 1 ? focusable[0] : focusable[index + 1]);
        next.focus();
      }
    }

    cancel.onclick = () => close(false);
    confirm.onclick = () => close(true);
    overlay.addEventListener('click', event => {
      if (event.target === overlay) close(false);
    });
    overlay.addEventListener('download-warning-dismiss', dismiss);
    document.addEventListener('keydown', onKey, true);
    document.body.append(overlay);
    cancel.focus();
  });
}
