#!/usr/bin/env python3
"""
Gofatho AI v6.0 — Official Sherpa-ONNX MMS-TTS Exporter (`facebook/mms-tts` -> `models/gof-script_latin`)
=========================================================================================================
Fixes the 401/RepositoryNotFoundError caused by `facebook/mms-tts-gof`:
In Meta's official `facebook/mms-tts` repository (https://huggingface.co/facebook/mms-tts) and the
official Sherpa-ONNX MMS guide (https://k2-fsa.github.io/sherpa/onnx/tts/mms.html), the Gofa (`gof`)
checkpoint is hosted under the subfolder `models/gof-script_latin/`:
  - https://huggingface.co/facebook/mms-tts/resolve/main/models/gof-script_latin/G_100000.pth
  - https://huggingface.co/facebook/mms-tts/resolve/main/models/gof-script_latin/config.json
  - https://huggingface.co/facebook/mms-tts/resolve/main/models/gof-script_latin/vocab.txt
"""

import os
import sys
import json
import shutil
import argparse
import collections
import subprocess
from typing import Dict, Any


def export_mms_tts_gof_to_sherpa_onnx(
    output_dir: str = "/content/drive/MyDrive/Gofa Ai/gofatho_sherpa_onnx_tts",
    repo_id: str = "facebook/mms-tts",
    lang_subfolder: str = "models/gof-script_latin",
    quantize_int8: bool = True,
    hf_token: str = None,
) -> Dict[str, Any]:
    import torch
    import onnx
    from huggingface_hub import hf_hub_download

    os.makedirs(output_dir, exist_ok=True)
    work_mms = "/tmp/mms_gof_export"
    os.makedirs(work_mms, exist_ok=True)

    print(f"[1/5] Downloading Gofa (`{lang_subfolder}`) VITS files from `{repo_id}` on Hugging Face...")
    g_pth = hf_hub_download(repo_id=repo_id, filename=f"{lang_subfolder}/G_100000.pth", token=hf_token)
    cfg_json = hf_hub_download(repo_id=repo_id, filename=f"{lang_subfolder}/config.json", token=hf_token)
    vocab_txt = hf_hub_download(repo_id=repo_id, filename=f"{lang_subfolder}/vocab.txt", token=hf_token)
    print(f"      Downloaded G_100000.pth ({os.path.getsize(g_pth)/(1024*1024):.1f} MB), config.json & vocab.txt")

    # 2. Generate Sherpa-ONNX `tokens.txt` from `vocab.txt` (official k2-fsa/sherpa-onnx MMS format)
    symbols = [x.replace("\n", "") for x in open(vocab_txt, encoding="utf-8").readlines()]
    all_upper = [i.upper() for i in symbols]
    duplicate = {item for item, count in collections.Counter(all_upper).items() if count > 1}

    tokens_path = os.path.join(output_dir, "tokens.txt")
    with open(tokens_path, "w", encoding="utf-8") as f:
        for idx, token in enumerate(symbols):
            f.write(f"{token} {idx}\n")
            if token.lower() != token.upper() and len(token.upper()) == 1 and token.upper() not in duplicate:
                f.write(f"{token.upper()} {idx}\n")
        if "7" not in symbols:
            f.write(f"7 {len(symbols)}\n")
    print(f"[2/5] Wrote {tokens_path} ({len(symbols)} base Gofatho character tokens)")

    # 3. Clone official `mms-meta/MMS` VITS definition (per https://k2-fsa.github.io/sherpa/onnx/tts/mms.html)
    mms_repo_dir = os.path.join(work_mms, "MMS")
    if not os.path.exists(os.path.join(mms_repo_dir, "vits")):
        print("[3/5] Fetching official `mms-meta/MMS` VITS SynthesizerTrn architecture...")
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://huggingface.co/spaces/mms-meta/MMS", mms_repo_dir],
            check=True,
        )
        # Build monotonic_align extension if Cython is available
        mono_dir = os.path.join(mms_repo_dir, "vits/monotonic_align")
        if os.path.exists(mono_dir):
            subprocess.run(["python3", "setup.py", "build"], cwd=mono_dir, check=False)
            for root_d, _, files_d in os.walk(os.path.join(mono_dir, "build")):
                for fn_d in files_d:
                    if fn_d.startswith("core") and fn_d.endswith(".so"):
                        shutil.copy2(os.path.join(root_d, fn_d), os.path.join(mono_dir, fn_d))
            init_py = os.path.join(mono_dir, "__init__.py")
            if os.path.exists(init_py):
                txt_i = open(init_py).read().replace(".monotonic_align.core", ".core")
                open(init_py, "w").write(txt_i)

    sys.path.insert(0, mms_repo_dir)
    sys.path.insert(0, os.path.join(mms_repo_dir, "vits"))
    from vits import utils
    from vits.models import SynthesizerTrn

    class OnnxModel(torch.nn.Module):
        def __init__(self, model: SynthesizerTrn):
            super().__init__()
            self.model = model

        def forward(self, x, x_lengths, noise_scale=0.667, length_scale=1.0, noise_scale_w=0.8):
            return self.model.infer(
                x=x,
                x_lengths=x_lengths,
                noise_scale=noise_scale,
                length_scale=length_scale,
                noise_scale_w=noise_scale_w,
            )[0]

    hps = utils.get_hparams_from_file(cfg_json)
    net_g = SynthesizerTrn(
        len(symbols),
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        **hps.model,
    )
    net_g.cpu()
    net_g.eval()
    utils.load_checkpoint(g_pth, net_g, None)
    wrapper = OnnxModel(net_g)
    wrapper.eval()

    x = torch.randint(low=1, high=min(10, len(symbols)), size=(50,), dtype=torch.int64).unsqueeze(0)
    x_length = torch.tensor([x.shape[1]], dtype=torch.int64)
    noise_scale = torch.tensor([1.0], dtype=torch.float32)
    length_scale = torch.tensor([1.0], dtype=torch.float32)
    noise_scale_w = torch.tensor([1.0], dtype=torch.float32)

    fp32_onnx_path = os.path.join(output_dir, "model.onnx")
    print(f"[4/5] Exporting Gofatho VITS ONNX graph -> {fp32_onnx_path}...")
    with torch.no_grad():
        torch.onnx.export(
            wrapper,
            (x, x_length, noise_scale, length_scale, noise_scale_w),
            fp32_onnx_path,
            opset_version=13,
            input_names=["x", "x_length", "noise_scale", "length_scale", "noise_scale_w"],
            output_names=["y"],
            dynamic_axes={
                "x": {0: "N", 1: "L"},
                "x_length": {0: "N"},
                "y": {0: "N", 2: "L"},
            },
        )

    meta_props = {
        "model_type": "vits",
        "comment": "mms",
        "url": "https://huggingface.co/facebook/mms-tts/tree/main/models/gof-script_latin",
        "add_blank": str(int(hps.data.add_blank)),
        "language": "Gofa (gof-script_latin)",
        "frontend": "characters",
        "n_speakers": str(int(hps.data.n_speakers)),
        "sample_rate": str(int(hps.data.sampling_rate)),
    }

    def attach_meta(fn_p: str):
        m = onnx.load(fn_p)
        for k, v in meta_props.items():
            entry = m.metadata_props.add()
            entry.key = str(k)
            entry.value = str(v)
        onnx.save(m, fn_p)

    attach_meta(fp32_onnx_path)
    fp32_mb = os.path.getsize(fp32_onnx_path) / (1024 * 1024)
    print(f"      Saved {fp32_onnx_path} ({fp32_mb:.2f} MB)")

    int8_onnx_path = os.path.join(output_dir, "model.int8.onnx")
    int8_mb = 0.0
    if quantize_int8:
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType
            print(f"[5/5] Quantizing FP32 -> INT8 ({int8_onnx_path})...")
            quantize_dynamic(
                model_input=fp32_onnx_path,
                model_output=int8_onnx_path,
                weight_type=QuantType.QUInt8,
            )
            attach_meta(int8_onnx_path)
            int8_mb = os.path.getsize(int8_onnx_path) / (1024 * 1024)
            print(f"      Saved quantized {int8_onnx_path} ({int8_mb:.2f} MB)!")
        except Exception as e:
            print(f"      [Note] Dynamic quantization skipped ({e}); copying FP32 to model.int8.onnx.")
            shutil.copy2(fp32_onnx_path, int8_onnx_path)
            int8_mb = fp32_mb

    manifest = {
        "repo_id": repo_id,
        "lang_subfolder": lang_subfolder,
        "language_iso": "gof",
        "sample_rate_hz": int(hps.data.sampling_rate),
        "tokens_file": "tokens.txt",
        "lexicon_file": "lexicon.txt",
        "fp32_onnx_file": "model.onnx",
        "fp32_size_mb": round(fp32_mb, 2),
        "int8_onnx_file": "model.int8.onnx",
        "int8_size_mb": round(int8_mb, 2),
        "metadata": meta_props,
    }
    manifest_path = os.path.join(output_dir, "model_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"✅ [OK] Wrote {manifest_path}!")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export facebook/mms-tts (models/gof-script_latin) to Sherpa-ONNX")
    parser.add_argument("--out-dir", "--output_dir", dest="out_dir", default="./gofatho_sherpa_onnx_tts")
    args = parser.parse_args()
    export_mms_tts_gof_to_sherpa_onnx(output_dir=args.out_dir)
