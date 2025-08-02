# train_trocr.py
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments
from datasets import Dataset
from PIL import Image
import torch
import pandas as pd
import os

# Paths
DATA_DIR = "custom_data"
IMG_DIR = os.path.join(DATA_DIR, "images")
CSV_FILE = os.path.join(DATA_DIR, "labels.csv")



# Load processor and model
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

# ✅ IMPORTANT: Set decoder_start_token_id
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.eos_token_id = processor.tokenizer.sep_token_id


# Load CSV
df = pd.read_csv(CSV_FILE)

# Preprocess function
def preprocess(example):
    image_path = os.path.join(IMG_DIR, example["filename"])
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values[0]
    labels = processor.tokenizer(example["text"], padding="max_length", truncation=True, max_length=32).input_ids
    return {"pixel_values": pixel_values, "labels": labels}

# Create dataset
dataset = Dataset.from_pandas(df)
dataset = dataset.map(preprocess)
dataset.set_format(type="torch", columns=["pixel_values", "labels"])

# Training arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./trocr-finetuned",
    per_device_train_batch_size=2,
    num_train_epochs=5,
    learning_rate=5e-5,
    logging_dir="./logs",
    save_steps=50,
    logging_steps=10,
    fp16=torch.cuda.is_available(),
)

# Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

# Train model
trainer.train()

# Save fine-tuned model
model.save_pretrained("./trocr-finetuned")
processor.save_pretrained("./trocr-finetuned")
