# 🎥 Video Quality Benchmark Tool

Open-source CLI tool for frame-level video quality analysis using FFmpeg + Python.

This tool benchmarks an encoded video against a source video using:

- VMAF
- PSNR
- SSIM (global + frame-level)
- Edge retention
- Noise difference
- Temporal flicker
- Audio sync lag

---

## 🚀 Requirements

- Python 3.9+
- FFmpeg compiled with libvmaf

Check FFmpeg:

```bash
ffmpeg -filters | grep vmaf
```

If not installed (macOS):

```bash
brew install ffmpeg
```

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/video-quality-benchmark.git
cd video-quality-benchmark
```

Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

Place your files:

```
source/source.mp4
encoded/encoded.mp4
```

Run:

```bash
python video_benchmark.py \
  --source source/source.mp4 \
  --encoded encoded/encoded.mp4 \
  --output result.json
```

---

## 🔁 Benchmark Another Provider

Simply replace the encoded file:

```bash
python video_benchmark.py \
  --source source/source.mp4 \
  --encoded encoded/aws_output.mp4
```

---

## 📊 Example Output

```json
{
  "vmaf": 97.30,
  "psnr": 46.98,
  "ssim_global": 0.9917,
  "frame_metrics": {
      "avg_frame_ssim": 0.9865,
      "min_frame_ssim": 0.9533,
      "edge_retention_ratio": 3.76,
      "avg_noise_difference": -0.047,
      "temporal_flicker_score": 73.70
  },
  "audio_sync_lag_samples": -2112
}
```

---

## 🧠 How It Works

- Extracts frames using FFmpeg
- Computes frame-level structural similarity
- Uses FFmpeg libvmaf for perceptual scoring
- Measures flicker and edge retention
- Checks audio alignment

---

## ⚠️ Notes

- Large videos may take time to process.
- For faster testing, modify frame extraction duration inside the script.

---

## 📄 License

MIT License
