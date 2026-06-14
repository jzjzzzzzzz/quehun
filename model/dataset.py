import os
import pandas as pd
from PIL import Image
from torch.utils.data import Dataset
import torch

class MahjongDataset(Dataset):
    def __init__(self, img_dir, csv_file, transform=None):
        self.img_dir = img_dir
        self.transform = transform

        self.data = pd.read_csv(csv_file)
        self.data.columns = [c.strip() for c in self.data.columns]

        self.filename_col = self.data.columns[0]
        self.label_col = self.data.columns[-1]

        self.labels = sorted(self.data[self.label_col].unique())
        self.label2idx = {l:i for i,l in enumerate(self.labels)}

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]

        img_path = os.path.join(self.img_dir, str(row[self.filename_col]))
        image = Image.open(img_path).convert("RGB")

        label = self.label2idx[row[self.label_col]]
        label = torch.tensor(label)

        if self.transform:
            image = self.transform(image)

        return image, label