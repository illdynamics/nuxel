// NuxTore catalog model: verification, safety gates and install state.
//
// Pure logic, no DOM: the same file is loaded by the NuxTore PWA and by the
// offline Node test suite (tests/test-catalog.js).  Everything here mirrors the
// authoritative Python verifier in tools/nuxtore-verify.py — same canonical
// form, same digest rule, same verdict vocabulary, same refusal reasons.
(function (root, factory) {
  function deps() {
    if (typeof module === 'object' && module.exports) {
      return { crypto: require('./nuxtore-crypto.js') };
    }
    return { crypto: root.NuxToreCrypto };
  }
  var api = factory(deps());
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.NuxToreCatalog = api;
}(typeof self !== 'undefined' ? self : this, function (deps) {
  'use strict';

  var C = deps.crypto;

  var VERDICT = {
    SIGNED_VERIFIED: 'SIGNED_VERIFIED',
    UNSIGNED_REFUSED: 'UNSIGNED_REFUSED',
    UNSIGNED_ALLOWED: 'UNSIGNED_ALLOWED',
    UNVERIFIED_ENGINE: 'UNVERIFIED_ENGINE',
    DIGEST_MISMATCH: 'DIGEST_MISMATCH',
    SIGNATURE_INVALID: 'SIGNATURE_INVALID',
    POLICY_VIOLATION: 'POLICY_VIOLATION',
    MISSING_BUNDLE: 'MISSING_BUNDLE'
  };

  var HARD_FAIL = [VERDICT.DIGEST_MISMATCH, VERDICT.SIGNATURE_INVALID,
                   VERDICT.POLICY_VIOLATION, VERDICT.MISSING_BUNDLE];

  var ID_RE = /^[A-Za-z0-9._-]+$/;
  var SHA_RE = /^[0-9a-f]{64}$/;

  function isAscii(s) {
    return typeof s === 'string' && !/[^\x20-\x7e]/.test(s);
  }

  function canonicalJson(obj) { return C.canonicalJson(obj); }

  // ---- digest of a bundle file list (must equal the package sha256) ---------
  async function bundleDigest(entries) {
    var sorted = entries.slice().sort(function (a, b) {
      return a.path < b.path ? -1 : (a.path > b.path ? 1 : 0);
    });
    return C.sha256Hex(canonicalJson(sorted));
  }

  function payloadOf(pkg) {
    var out = {};
    Object.keys(pkg).forEach(function (k) { if (k !== 'signature') out[k] = pkg[k]; });
    return out;
  }

  // ---- one package ---------------------------------------------------------
  async function verifyPackage(pkg, ctx) {
    var problems = [], notes = [];
    var policy = ctx.policy || {};
    var signedOk = false, signatureState = 'unsigned', files = null;

    ['id', 'name', 'version', 'sha256', 'bundle', 'source', 'install'].forEach(function (f) {
      if (pkg[f] === undefined || pkg[f] === null) problems.push('missing field ' + f);
    });
    if (!ID_RE.test(String(pkg.id || ''))) problems.push('package id is not a safe ASCII identifier');
    if (!SHA_RE.test(String(pkg.sha256 || ''))) problems.push('sha256 field is not a 64-hex digest');

    var src = pkg.source || {};
    var allowed = policy.allowed_source_types || ['local-bundle'];
    if (allowed.indexOf(src.type) === -1) problems.push('source type "' + src.type + '" not allowed by policy');
    Object.keys(src).forEach(function (k) {
      if (typeof src[k] === 'string' && src[k].indexOf('http://') !== -1) {
        problems.push('http source URI refused by policy (allow_http=false)');
      }
    });
    if ((pkg.size_bytes || 0) > (policy.max_package_bytes || Number.MAX_SAFE_INTEGER)) {
      problems.push('package exceeds max_package_bytes');
    }
    ['id', 'name', 'version', 'summary', 'description', 'sha256', 'bundle', 'license'].forEach(function (f) {
      if (pkg[f] !== undefined && !isAscii(pkg[f])) {
        problems.push('signed field ' + f + ' must be ASCII (canonical form)');
      }
    });

    // ---- bundle manifest + staged files ----
    var expectedDigest = null;
    if (ctx.readBundle) {
      var bundle = await ctx.readBundle(pkg.bundle);
      if (!bundle) {
        problems.push('bundle manifest missing: ' + pkg.bundle);
        if (!problems.some(function (p) { return p.indexOf('bundle') === 0; })) {
          problems.push('bundle manifest missing');
        }
      } else {
        files = Array.isArray(bundle) ? bundle : bundle.files;
        if (!Array.isArray(files)) {
          problems.push('bundle manifest is not a file list');
        } else {
          expectedDigest = await bundleDigest(files);
          if (expectedDigest !== pkg.sha256) problems.push('bundle digest does not match package sha256');
          notes.push(files.length + ' files, ' + formatBytes(pkg.size_bytes || 0));
          if (ctx.verifyFiles !== false && ctx.readFile) {
            var missing = 0, mismatched = 0, unreadable = 0;
            for (var i = 0; i < files.length; i++) {
              var data = await ctx.readFile(files[i].path);
              if (data === null || data === undefined) { missing++; continue; }
              var h = await C.sha256Hex(data);
              if (h === null) { unreadable++; continue; }
              if (h !== files[i].sha256) mismatched++;
            }
            if (missing) problems.push(missing + ' of ' + files.length + ' staged files are missing');
            if (mismatched) problems.push(mismatched + ' of ' + files.length + ' staged files have a different digest');
            if (unreadable) notes.push('file hashing unavailable in this engine');
          }
        }
      }
    } else {
      notes.push('bundle not read in this environment');
    }

    // ---- signature ----
    var sig = pkg.signature;
    if (!problems.length) {
      if (!sig) {
        signatureState = 'unsigned';
        notes.push('no signature (unsigned package)');
      } else if (sig.alg !== 'ed25519') {
        problems.push('unsupported signature algorithm "' + sig.alg + '"');
      } else {
        var pub = (ctx.publicKeys || {})[sig.key_id];
        if (!pub) {
          problems.push('unknown signing key "' + sig.key_id + '" (no public key on device)');
        } else {
          var res = await C.verifyEd25519(canonicalJson(payloadOf(pkg)), sig.value, pub);
          if (res === null) {
            signatureState = 'engine-unsupported';
            notes.push('Ed25519 unsupported by this engine — signature not checked here');
          } else if (res !== true) {
            problems.push('ed25519 signature does not verify over the payload');
          } else {
            signedOk = true;
            signatureState = 'valid';
            notes.push('signed by ' + sig.key_id);
          }
        }
      }
    }

    // ---- verdict -----------------------------------------------------------
    var verdict;
    if (problems.some(function (p) { return /digest/.test(p); })) verdict = VERDICT.DIGEST_MISMATCH;
    else if (problems.some(function (p) { return /signature/.test(p); })) verdict = VERDICT.SIGNATURE_INVALID;
    else if (problems.some(function (p) { return /bundle manifest missing|not a file list/.test(p); })) verdict = VERDICT.MISSING_BUNDLE;
    else if (problems.length) verdict = VERDICT.POLICY_VIOLATION;
    else if (signedOk) verdict = VERDICT.SIGNED_VERIFIED;
    else if (signatureState === 'engine-unsupported') verdict = VERDICT.UNVERIFIED_ENGINE;
    else verdict = VERDICT.UNSIGNED_REFUSED;

    return {
      id: pkg.id, name: pkg.name, version: pkg.version, category: pkg.category,
      summary: pkg.summary, description: pkg.description, license: pkg.license,
      size_bytes: pkg.size_bytes, file_count: pkg.file_count,
      sha256: pkg.sha256, installer: pkg.install, source: pkg.source,
      requires: pkg.requires || [], capabilities: pkg.capabilities || [],
      stateHint: pkg.state_hint || 'available',
      signatureState: signatureState, signed: !!signedOk,
      verdict: verdict, problems: problems, notes: notes,
      hardFail: HARD_FAIL.indexOf(verdict) !== -1
    };
  }

  // ---- whole catalog -------------------------------------------------------
  async function verifyCatalog(catalog, ctx) {
    ctx = ctx || {};
    var policy = (catalog && catalog.policy) || {};
    var seal = { status: 'unknown', keyId: null, detail: '' };
    var publisher = (catalog && catalog.publisher) || {};
    var keyId = publisher.key_id || null;
    seal.keyId = keyId;

    if (!catalog || catalog.schema_version !== 1) {
      return { ok: false, seal: { status: 'invalid', keyId: keyId, detail: 'unsupported schema_version' },
               packages: [], generated: null };
    }
    if (policy.allow_external_publish !== false) {
      return { ok: false, seal: { status: 'invalid', keyId: keyId,
               detail: 'policy.allow_external_publish must be false — NuxTore never publishes' },
               packages: [], generated: catalog.generated };
    }
    // The catalog seal is the publisher's own public key being present and usable;
    // per-package signatures are what gate an install.
    var pub = (ctx.publicKeys || {})[keyId];
    if (!pub) {
      seal.status = 'no-key';
      seal.detail = 'publisher public key ' + keyId + ' is not on the device';
    } else if (await C.verifyEd25519('nuxel-catalog-seal:' + (catalog.catalog_id || ''), 
                                    ctx.sealSignature || '', pub) === null) {
      seal.status = 'engine-unsupported';
      seal.detail = 'this engine cannot verify Ed25519; run tools/nuxtore-verify.py';
    } else {
      seal.status = 'key-present';
      seal.detail = 'publisher key ' + keyId + ' loaded; each package is verified individually';
    }

    var packages = [];
    var list = (catalog.packages || []);
    for (var i = 0; i < list.length; i++) {
      packages.push(await verifyPackage(list[i], { policy: policy, publicKeys: ctx.publicKeys || {},
                                                   readBundle: ctx.readBundle, readFile: ctx.readFile,
                                                   verifyFiles: ctx.verifyFiles }));
    }
    var ok = !packages.some(function (p) { return p.hardFail; });
    return { ok: ok, seal: seal, packages: packages, generated: catalog.generated,
             catalogId: catalog.catalog_id, policy: policy, notice: catalog.notice || '' };
  }

  // ---- safety gate ---------------------------------------------------------
  function installDecision(pkgResult, opts) {
    opts = opts || {};
    if (!pkgResult) return { allowed: false, reason: 'unknown package' };
    if (pkgResult.hardFail) {
      return { allowed: false, reason: 'integrity failure (' + pkgResult.verdict + '): ' +
               (pkgResult.problems[0] || 'verification failed') };
    }
    if (pkgResult.verdict === VERDICT.SIGNED_VERIFIED) {
      return { allowed: true, reason: 'signature and bundle digest verified' };
    }
    if (pkgResult.verdict === VERDICT.UNSIGNED_REFUSED) {
      if (!opts.allowUnsigned) {
        return { allowed: false, reason: 'unsigned package — the catalog requires a signature' };
      }
      if (opts.confirmedId !== pkgResult.id) {
        return { allowed: false, reason: 'unsigned install needs a typed confirmation of the package id' };
      }
      return { allowed: true, warning: 'installing UNVERIFIED package — no signature covers this bundle' };
    }
    if (pkgResult.verdict === VERDICT.UNVERIFIED_ENGINE) {
      if (!opts.allowUnsigned || opts.confirmedId !== pkgResult.id) {
        return { allowed: false, reason: 'signature not checkable in this engine; confirm the package id to proceed' };
      }
      return { allowed: true, warning: 'signature NOT checked in this engine — verify offline with tools/nuxtore-verify.py' };
    }
    return { allowed: false, reason: 'package is not installable (' + pkgResult.verdict + ')' };
  }

  // ---- install state -------------------------------------------------------
  function emptyState() {
    return { schema_version: 1, installed: {}, removed: [], log: [] };
  }

  function applyInstall(state, pkgResult, when) {
    var next = clone(state);
    next.installed[pkgResult.id] = {
      version: pkgResult.version, at: when || null,
      sha256: pkgResult.sha256, signed: pkgResult.signed,
      verdict: pkgResult.verdict
    };
    next.removed = next.removed.filter(function (id) { return id !== pkgResult.id; });
    next.log = pushLog(next.log, 'install ' + pkgResult.id + ' ' + pkgResult.version +
                        (pkgResult.signed ? ' (signed)' : ' (UNVERIFIED)'), when);
    return next;
  }

  function applyRemove(state, id, when) {
    var next = clone(state);
    delete next.installed[id];
    if (next.removed.indexOf(id) === -1) next.removed = next.removed.concat([id]);
    next.log = pushLog(next.log, 'remove ' + id, when);
    return next;
  }

  function pushLog(log, line, when) {
    var l = (log || []).slice(-199);
    l.push({ at: when || null, line: line });
    return l;
  }

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function plan(state, report) {
    var installed = [], available = [], blocked = [], removable = [];
    (report.packages || []).forEach(function (p) {
      var have = state.installed[p.id];
      var entry = { pkg: p, installed: !!have, installedVersion: have ? have.version : null,
                    updatable: !!(have && have.version !== p.version) };
      if (p.hardFail) blocked.push(entry);
      else if (have) { installed.push(entry); if (entry.updatable) available.push(entry); }
      else available.push(entry);
      if (have && p.stateHint === 'installed' && p.installer && p.installer.app_id === p.id) removable.push(entry);
    });
    return { installed: installed, available: available, blocked: blocked, removable: removable,
             counts: { installed: installed.length, available: available.length, blocked: blocked.length } };
  }

  function formatBytes(n) {
    if (n === null || n === undefined) return '—';
    var units = ['B', 'KiB', 'MiB', 'GiB'];
    var i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (i === 0 ? String(n) : n.toFixed(n < 10 ? 1 : 0)) + ' ' + units[i];
  }

  return {
    VERDICT: VERDICT,
    verifyCatalog: verifyCatalog,
    verifyPackage: verifyPackage,
    bundleDigest: bundleDigest,
    payloadOf: payloadOf,
    installDecision: installDecision,
    emptyState: emptyState,
    applyInstall: applyInstall,
    applyRemove: applyRemove,
    plan: plan,
    formatBytes: formatBytes,
    canonicalJson: canonicalJson
  };
}));
