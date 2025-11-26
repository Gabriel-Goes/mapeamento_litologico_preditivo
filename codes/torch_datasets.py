from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset


class PixelSpectralDataset(Dataset):
    def __init__(self, npz_path: str):
        data = np.load(npz_path)
        self.X = data["X"].astype("float32")
        self.y = data["y"].astype("int64")

        self.mean = self.X.mean(axis=0, keepdims=True)
        self.std = self.X.std(axis=0, keepdims=True)
        self.std[self.std == 0] = 1.0
        self.X = (self.X - self.mean) / self.std

        self.C = self.X.shape[1]

    def __len__(self) -> int:
        return int(self.X.shape[0])

    def __getitem__(self, idx: int):
        x = self.X[idx]
        y = self.y[idx]
        x_t = torch.from_numpy(x).view(self.C, 1, 1)
        y_t = torch.tensor(y, dtype=torch.long)
        return x_t, y_t


class PatchDataset(Dataset):
    def __init__(self, npz_path: str):
        data = np.load(npz_path)
        self.X = data["X"].astype("float32")
        self.y = data["y"].astype("int64")

        self.N, self.C, self.H, self.W = self.X.shape

        classes = np.unique(self.y)
        self.classes = classes
        self.label_to_idx = {lab: i for i, lab in enumerate(classes)}
        self.idx_to_label = {i: lab for i, lab in enumerate(classes)}

        self.y = np.vectorize(self.label_to_idx.get)(self.y)

        X_flat = self.X.reshape(self.N, self.C, -1)

        mean = X_flat.mean(axis=(0, 2))
        std = X_flat.std(axis=(0, 2))
        std[std == 0] = 1.0

        mean = mean.reshape(1, self.C, 1, 1)
        std = std.reshape(1, self.C, 1, 1)

        self.X = (self.X - mean) / std

    def __len__(self) -> int:
        return int(self.N)

    def __getitem__(self, idx: int):
        x = torch.from_numpy(self.X[idx])
        y = torch.tensor(self.y[idx], dtype=torch.long)
        return x, y
