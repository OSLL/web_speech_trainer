from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

app = FastAPI()

MODEL_PATH = "/models/rut5"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=False)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
model.eval()


class GenerateRequest(BaseModel):
    prompt: str
    max_length: int = 96
    num_beams: int = 5


@app.post("/generate")
def generate(req: GenerateRequest):
    inputs = tokenizer(req.prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_length=req.max_length,
            num_beams=req.num_beams,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    return {"text": text}


class TokenizeRequest(BaseModel):
    text: str


@app.post("/tokenize")
def tokenize(req: TokenizeRequest):
    tokens = tokenizer.tokenize(req.text)
    return {"tokens": tokens, "length": len(tokens)}


@app.get("/max_tokens")
def max_tokens():
    return {"max_tokens": tokenizer.model_max_length}
