import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import DataLoader, random_split

from model.dataset import MahjongDataset
from model import CNN

device = "cuda" if torch.cuda.is_available() else "cpu"

IMG_DIR = "../dataset/tiles-resized"
CSV_FILE = "../dataset/tiles-data/data.csv"

transform = transforms.Compose([
    transforms.Resize((128,128)),
    transforms.RandomRotation(10),
    transforms.ToTensor()
])

dataset = MahjongDataset(IMG_DIR, CSV_FILE, transform)

# ⭐ 切分训练/验证
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_ds, val_ds = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=32)

model = CNN(len(dataset.labels)).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(15):
    model.train()
    total_loss = 0

    for x, y in train_loader:
        x, y = x.to(device), y.to(device)

        out = model(x)
        loss = criterion(out, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    # ===== 验证 =====
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for x, y in val_loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            pred = out.argmax(1)

            correct += (pred == y).sum().item()
            total += y.size(0)

    acc = correct / total

    print(f"Epoch {epoch+1} | loss={total_loss:.3f} | acc={acc:.3f}")

torch.save(model.state_dict(), "../model.pth")
print("训练完成")