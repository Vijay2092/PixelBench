import os
import json
import argparse
import subprocess
import numpy as np
import cv2
import shutil
import tempfile
import soundfile as sf
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

TMP_SRC = "tmp_frames_src"
TMP_ENC = "tmp_frames_enc"

# -----------------------------
# Utility: Run FFmpeg Command
# -----------------------------
def run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr

# -----------------------------
# VMAF
# -----------------------------
def compute_vmaf(src, enc):
    vmaf_log = "vmaf_log.json"

    cmd = [
        "ffmpeg", "-y",
        "-i", enc,
        "-i", src,
        "-lavfi", f"libvmaf=log_path={vmaf_log}:log_fmt=json",
        "-f", "null", "-"
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(vmaf_log):
        with open(vmaf_log, "r") as f:
            data = json.load(f)
            return data["pooled_metrics"]["vmaf"]["mean"]

    return None

# -----------------------------
# PSNR
# -----------------------------
def compute_psnr(src, enc):
    cmd = [
        "ffmpeg", "-i", enc, "-i", src,
        "-lavfi", "psnr",
        "-f", "null", "-"
    ]
    output = run_ffmpeg(cmd)
    for line in output.split("\n"):
        if "average:" in line:
            return float(line.split("average:")[1].split()[0])
    return None

# -----------------------------
# SSIM
# -----------------------------
def compute_ssim_global(src, enc):
    cmd = [
        "ffmpeg", "-i", enc, "-i", src,
        "-lavfi", "ssim",
        "-f", "null", "-"
    ]
    output = run_ffmpeg(cmd)
    for line in output.split("\n"):
        if "All:" in line:
            return float(line.split("All:")[1].split()[0])
    return None

# -----------------------------
# Frame Extraction
# -----------------------------
def extract_frames(video, output_dir, prefix):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    pattern = os.path.join(output_dir, f"{prefix}_%05d.png")

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vsync", "0",
        pattern
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    files = sorted(
        [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".png")]
    )

    return files

# -----------------------------
# Frame-Level Metrics
# -----------------------------
def frame_level_metrics(src_frames, enc_frames):
    ssims = []
    flicker_scores = []
    edge_ratios = []
    noise_diff = []

    prev_mean_luma = None
    min_len = min(len(src_frames), len(enc_frames))

    for i in tqdm(range(min_len)):
        src_img = cv2.imread(src_frames[i], 0)
        enc_img = cv2.imread(enc_frames[i], 0)

        if src_img is None or enc_img is None:
            continue

        # SSIM
        s = ssim(src_img, enc_img)
        ssims.append(s)

        # Edge retention
        edge_src = cv2.Laplacian(src_img, cv2.CV_64F).var()
        edge_enc = cv2.Laplacian(enc_img, cv2.CV_64F).var()
        edge_ratios.append(edge_enc / (edge_src + 1e-6))

        # Noise preservation
        blur_src = cv2.GaussianBlur(src_img, (5, 5), 0)
        blur_enc = cv2.GaussianBlur(enc_img, (5, 5), 0)

        noise_src = src_img - blur_src
        noise_enc = enc_img - blur_enc

        noise_diff.append(np.std(noise_enc) - np.std(noise_src))

        # Temporal flicker
        mean_luma = np.mean(enc_img)
        if prev_mean_luma is not None:
            flicker_scores.append(abs(mean_luma - prev_mean_luma))
        prev_mean_luma = mean_luma

    return {
        "avg_frame_ssim": float(np.mean(ssims)) if ssims else 0.0,
        "min_frame_ssim": float(np.min(ssims)) if ssims else 0.0,
        "edge_retention_ratio": float(np.median(edge_ratios)) if edge_ratios else 0.0,
        "avg_noise_difference": float(np.mean(noise_diff)) if noise_diff else 0.0,
        "temporal_flicker_score": float(np.mean(flicker_scores)) if flicker_scores else 0.0
    }

# -----------------------------
# Audio Sync
# -----------------------------
def audio_sync(src, enc):
    duration = 10

    src_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    enc_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-t", str(duration),
        "-ac", "1",
        "-ar", "16000",
        src_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "ffmpeg", "-y", "-i", enc,
        "-t", str(duration),
        "-ac", "1",
        "-ar", "16000",
        enc_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    y1, sr = sf.read(src_wav)
    y2, sr = sf.read(enc_wav)

    min_len = min(len(y1), len(y2))
    y1 = y1[:min_len]
    y2 = y2[:min_len]

    corr = np.correlate(y1, y2, "full")
    lag = corr.argmax() - (len(y2) - 1)

    return int(lag)

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Video Quality Benchmark Tool")
    parser.add_argument("--source", required=True)
    parser.add_argument("--encoded", required=True)
    parser.add_argument("--output", default="benchmark_result.json")

    args = parser.parse_args()

    print("Extracting frames...")
    src_frames = extract_frames(args.source, TMP_SRC, "src")
    enc_frames = extract_frames(args.encoded, TMP_ENC, "enc")

    if len(src_frames) != len(enc_frames):
        print("⚠ Warning: Frame count mismatch!")
        print("Source:", len(src_frames))
        print("Encoded:", len(enc_frames))

    print("Computing metrics...")

    results = {
        "vmaf": compute_vmaf(args.source, args.encoded),
        "psnr": compute_psnr(args.source, args.encoded),
        "ssim_global": compute_ssim_global(args.source, args.encoded),
        "frame_metrics": frame_level_metrics(src_frames, enc_frames),
        "audio_sync_lag_samples": audio_sync(args.source, args.encoded)
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=4)

    print("\nBenchmark Complete")
    print(json.dumps(results, indent=4))

if __name__ == "__main__":
    main()
