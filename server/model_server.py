# server/model_server.py
from fastapi import FastAPI
from pydantic import BaseModel
import torch
import base64
import io
from PIL import Image
import torchvision.transforms as T
import os

app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'model.pt')

transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

if not os.path.exists(MODEL_PATH):
    raise RuntimeError(f"Model file not found: {MODEL_PATH}. Run training and place exported TorchScript at this path.")

model = torch.jit.load(MODEL_PATH, map_location=device)
model.eval()
model.to(device)

class PredictReq(BaseModel):
    image_b64: str
    challenge: str | None = None

@app.post('/predict')
def predict(req: PredictReq):
    try:
        image_bytes = base64.b64decode(req.image_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        x = transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            pred = model(x).squeeze(0).cpu().item()
        pred = max(0.0, min(1.0, float(pred)))
        confidence = 0.95
        return {'pred': pred, 'confidence': confidence}
    except Exception as e:
        return {'error': str(e), 'pred': 0.5, 'confidence': 0.0}
