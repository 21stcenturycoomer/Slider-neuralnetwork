# scripts/train.py

import os
import json
import base64
import io
import argparse
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
import torchvision.transforms as T
from torchvision import models
from tqdm import tqdm

class CaptchaDataset(Dataset):
    def __init__(self, jsonl_path, transform=None):
        self.rows = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not obj.get("image_b64") or obj.get("response") is None:
                    continue
                self.rows.append(obj)
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        image = Image.open(io.BytesIO(base64.b64decode(row["image_b64"]))).convert("RGB")
        if self.transform:
            image = self.transform(image)

        response = row["response"]
        if isinstance(response, str):
            try:
                response = float(response)
            except:
                response = 0.5

        # 归一化到 0..1
        if response < 0:
            response = 0.0
        if response > 1:
            response = 1.0

        return image, torch.tensor([response], dtype=torch.float32)


def build_model():
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Linear(128, 1)
    )
    return model


def train(args):
    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    dataset = CaptchaDataset(args.jsonl, transform=transform)
    if len(dataset) < 2:
        raise ValueError("Not enough data. Please collect more samples first.")

    train_size = int(len(dataset) * 0.8)
    val_size = len(dataset) - train_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model().to(device)
    loss_fn = nn.L1Loss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_val = 1e9
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for imgs, targets in tqdm(train_loader, desc=f"Epoch {epoch}"):
            imgs = imgs.to(device)
            targets = targets.to(device).squeeze(1)
            optimizer.zero_grad()
            preds = model(imgs).squeeze(1)
            loss = loss_fn(preds, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)

        train_loss = total_loss / len(train_ds)

        model.eval()
        total_val = 0.0
        with torch.no_grad():
            for imgs, targets in val_loader:
                imgs = imgs.to(device)
                targets = targets.to(device).squeeze(1)
                preds = model(imgs).squeeze(1)
                total_val += torch.abs(preds - targets).sum().item()

        val_mae = total_val / len(val_ds)
        print(f"Epoch {epoch}: train_loss={train_loss:.4f}, val_mae={val_mae:.4f}")

        if val_mae < best_val:
            best_val = val_mae
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            torch.save(model.state_dict(), args.out)
            print(f"Saved best model to {args.out}")

    model.load_state_dict(torch.load(args.out, map_location=device))
    model.eval()
    example_input = torch.randn(1, 3, 224, 224).to(device)
    traced = torch.jit.trace(model, example_input)
    os.makedirs(os.path.dirname(args.export), exist_ok=True)
    traced.save(args.export)
    print(f"Exported TorchScript model to {args.export}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", default="data/collected/samples.jsonl")
    parser.add_argument("--out", default="server/models/best.pth")
    parser.add_argument("--export", default="server/models/model.pt")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()
    train(args)
