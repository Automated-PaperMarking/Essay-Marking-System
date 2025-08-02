from huggingface_hub import snapshot_download

# This will download the model repo to ./nanonets_ocr_s/
snapshot_download(repo_id="nanonets/Nanonets-OCR-s", local_dir="nanonets_ocr_s")
