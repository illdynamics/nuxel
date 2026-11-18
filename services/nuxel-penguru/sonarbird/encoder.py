"""Offline MiniLM WordPiece encoder with masked pooling and L2 normalization."""
from pathlib import Path
import numpy as np


class Encoder:
    def __init__(self, package, threads=2, graph='encoder.onnx'):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        package = Path(package)
        self.tokenizer = Tokenizer.from_file(str(package / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding(pad_id=0, pad_token='[PAD]')
        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, min(4, threads))
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(package / graph), options,
                                            providers=['CPUExecutionProvider'])
        self.names = {x.name for x in self.session.get_inputs()}

    def encode(self, texts):
        batch = self.tokenizer.encode_batch(texts)
        inputs = {'input_ids': np.array([x.ids for x in batch], dtype=np.int64),
                  'attention_mask': np.array([x.attention_mask for x in batch], dtype=np.int64),
                  'token_type_ids': np.array([x.type_ids for x in batch], dtype=np.int64)}
        hidden = self.session.run(None, {k:v for k,v in inputs.items() if k in self.names})[0]
        if hidden.ndim != 3 or hidden.shape[-1] != 384:
            raise ValueError('MiniLM must output 384-dimensional token embeddings')
        mask = inputs['attention_mask'][..., None]
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
        vectors = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        if not np.isfinite(vectors).all():
            raise ValueError('Non-finite embeddings')
        return vectors
