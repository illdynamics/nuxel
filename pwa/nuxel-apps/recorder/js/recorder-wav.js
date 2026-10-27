/* Nuxel Recorder — 16-bit PCM WAV encoder (PWNAGE-30000).
   Pure, DOM-free module so the WAV structure is unit-testable in node.  It
   encodes Float32 mono/stereo sample buffers into a complete RIFF/WAVE file
   with a valid fmt + data chunk.  No codec is ever mislabelled as WAV. */
(function (global) {
  'use strict';
  function encodeWav(channels, sampleRate, samples) {
    if (!Array.isArray(samples) || samples.length === 0) throw new Error('no samples');
    if (!Array.isArray(channels)) channels = [samples];
    var chCount = channels.length;
    if (chCount < 1 || chCount > 2) throw new Error('unsupported channel count');
    var frameCount = channels[0].length;
    for (var i = 0; i < chCount; i++) {
      if (channels[i].length !== frameCount) throw new Error('channel length mismatch');
    }
    var bytesPerSample = 2;
    var blockAlign = chCount * bytesPerSample;
    var byteRate = sampleRate * blockAlign;
    var dataSize = frameCount * blockAlign;
    var buf = new ArrayBuffer(44 + dataSize);
    var view = new DataView(buf);
    function writeStr(off, s) { for (var j = 0; j < s.length; j++) view.setUint8(off + j, s.charCodeAt(j)); }
    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);            // PCM
    view.setUint16(22, chCount, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);           // bits per sample
    writeStr(36, 'data');
    view.setUint32(40, dataSize, true);
    var off = 44;
    for (var f = 0; f < frameCount; f++) {
      for (var c = 0; c < chCount; c++) {
        var v = channels[c][f];
        if (v > 1) v = 1; else if (v < -1) v = -1;
        var s = v < 0 ? v * 0x8000 : v * 0x7FFF;
        view.setInt16(off, Math.round(s), true);
        off += 2;
      }
    }
    return new Uint8Array(buf);
  }

  function wavHeaderInfo(bytes) {
    if (!bytes || bytes.length < 44) return { valid: false, reason: 'too short' };
    var b = bytes;
    var riff = String.fromCharCode(b[0], b[1], b[2], b[3]);
    var wave = String.fromCharCode(b[8], b[9], b[10], b[11]);
    var fmt = String.fromCharCode(b[12], b[13], b[14], b[15]);
    if (riff !== 'RIFF' || wave !== 'WAVE' || fmt !== 'fmt ') return { valid: false, reason: 'bad magic' };
    var view = new DataView(b.buffer, b.byteOffset, b.byteLength);
    return {
      valid: true,
      channels: view.getUint16(22, true),
      sampleRate: view.getUint32(24, true),
      bitsPerSample: view.getUint16(34, true),
      dataSize: view.getUint32(40, true),
      totalBytes: b.length
    };
  }

  var api = { encodeWav: encodeWav, wavHeaderInfo: wavHeaderInfo, VERSION: 1 };
  global.NuxelWav = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
