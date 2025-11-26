from __future__ import annotations

from typing import Dict, Any, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import confusion_matrix, classification_report

from torch_datasets import PixelSpectralDataset, PatchDataset
from models_cnn import PixelCNN, PatchCNN


def _make_device(device: Optional[str] = None) -> torch.device:
    if device is not None:
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def print_class_distribution(y: np.ndarray) -> None:
    unique, counts = np.unique(y, return_counts=True)
    print("Distribuição de classes:")
    for u, c in zip(unique, counts):
        print(f"  classe={u}: n={c}")


def evaluate_model(
    model: nn.Module,
    data_loader: DataLoader,
    device: torch.device,
) -> Dict[str, Any]:
    model.eval()
    all_preds = []
    all_true = []

    with torch.no_grad():
        for X_batch, y_batch in data_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            logits = model(X_batch)
            preds = logits.argmax(dim=1)
            all_preds.append(preds.cpu().numpy())
            all_true.append(y_batch.cpu().numpy())

    if not all_true:
        raise RuntimeError("Loader de avaliação vazio.")

    y_true = np.concatenate(all_true)
    y_pred = np.concatenate(all_preds)

    acc = float((y_true == y_pred).mean())
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(y_true, y_pred)

    return {
        "accuracy": acc,
        "confusion_matrix": cm,
        "classification_report": report,
        "y_true": y_true,
        "y_pred": y_pred,
    }


def train_pixel_cnn(
    npz_path: str,
    n_epochs: int = 25,
    batch_size: int = 512,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    device: Optional[str] = None,
    val_fraction: float = 0.2,
) -> Tuple[nn.Module, Dict[str, Any]]:
    d = PixelSpectralDataset(npz_path)
    n_classes = int(d.y.max() + 1)
    in_channels = d.C

    y_all = d.y
    print_class_distribution(y_all)

    n_total = len(d)
    n_val = int(val_fraction * n_total)
    n_train = n_total - n_val
    train_ds, val_ds = random_split(d, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    dev = _make_device(device)
    model = PixelCNN(in_channels=in_channels, n_classes=n_classes).to(dev)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    history = {"train_loss": [], "val_acc": []}

    for epoch in range(1, n_epochs + 1):
        model.train()
        running_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(dev)
            y_batch = y_batch.to(dev)

            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * X_batch.size(0)

        train_loss = running_loss / n_train
        eval_stats = evaluate_model(model, val_loader, dev)
        val_acc = eval_stats["accuracy"]

        history["train_loss"].append(train_loss)
        history["val_acc"].append(val_acc)

        print(f"[PIXEL CNN] Epoch {epoch:02d} | train_loss={train_loss:.4f} | val_acc={val_acc:.4f}")

    final_eval = evaluate_model(model, val_loader, dev)
    return model, {"history": history, "eval": final_eval}


def train_patch_cnn(
    npz_path: str,
    n_epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    device: Optional[str] = None,
    val_fraction: float = 0.2,
) -> Tuple[nn.Module, Dict[str, Any]]:
    d = PatchDataset(npz_path)
    n_classes = len(d.classes)
    in_channels = d.C

    print("Classes originais:", d.classes)
    print_class_distribution(d.y)

    n_total = len(d)
    n_val = int(val_fraction * n_total)
    n_train = n_total - n_val
    train_ds, val_ds = random_split(d, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    dev = _make_device(device)
    model = PatchCNN(in_channels=in_channels, n_classes=n_classes).to(dev)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    history = {"train_loss": [], "val_acc": []}

    for epoch in range(1, n_epochs + 1):
        model.train()
        running_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(dev)
            y_batch = y_batch.to(dev)

            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * X_batch.size(0)

        train_loss = running_loss / n_train
        eval_stats = evaluate_model(model, val_loader, dev)
        val_acc = eval_stats["accuracy"]

        history["train_loss"].append(train_loss)
        history["val_acc"].append(val_acc)

        print(f"[PATCH CNN] Epoch {epoch:02d} | train_loss={train_loss:.4f} | val_acc={val_acc:.4f}")

    final_eval = evaluate_model(model, val_loader, dev)
    return model, {"history": history, "eval": final_eval}
