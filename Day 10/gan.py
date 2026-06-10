import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt

# -----------------------------
# Generator
# -----------------------------
class Generator(nn.Module):
    def __init__(self, z_dim):
        super().__init__()
        self.model = nn.Sequential(
            # Input: z_dim x 1 x 1
            nn.ConvTranspose2d(z_dim, 512, kernel_size=4, stride=1, padding=0),   # 1x1 -> 4x4
            nn.BatchNorm2d(512),
            nn.ReLU(True),

            nn.ConvTranspose2d(512, 256, kernel_size=4, stride=2, padding=1),     # 4x4 -> 8x8
            nn.BatchNorm2d(256),
            nn.ReLU(True),

            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),     # 8x8 -> 16x16
            nn.BatchNorm2d(128),
            nn.ReLU(True),

            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),      # 16x16 -> 32x32
            nn.BatchNorm2d(64),
            nn.ReLU(True),

            nn.ConvTranspose2d(64, 1, kernel_size=4, stride=2, padding=1),        # 32x32 -> 64x64
            nn.Tanh()
        )

    def forward(self, x):
        return self.model(x)


# -----------------------------
# Discriminator
# -----------------------------
class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Sequential(
            # Input: 1 x 64 x 64
            nn.Conv2d(1, 64, kernel_size=4, stride=2, padding=1),    # 64x64 -> 32x32
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),  # 32x32 -> 16x16
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1), # 16x16 -> 8x8
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(256, 512, kernel_size=4, stride=2, padding=1), # 8x8 -> 4x4
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Flatten(),
            nn.Linear(512 * 4 * 4, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)


# -----------------------------
# Device
# -----------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# -----------------------------
# Hyperparameters
# -----------------------------
batch_size = 128
learning_rate = 0.0002
z_dim = 100
epochs = 10

# -----------------------------
# Transform and Dataset
# Resize MNIST from 28x28 to 64x64
# -----------------------------
transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

dataset = datasets.MNIST(
    root="./data",
    train=True,
    download=True,
    transform=transform
)

dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

# -----------------------------
# Initialize models
# -----------------------------
generator = Generator(z_dim).to(device)
discriminator = Discriminator().to(device)

# Loss and optimizers
criterion = nn.BCELoss()

optimizer_g = optim.Adam(generator.parameters(), lr=learning_rate, betas=(0.5, 0.999))
optimizer_d = optim.Adam(discriminator.parameters(), lr=learning_rate, betas=(0.5, 0.999))

# -----------------------------
# Function to display generated images
# -----------------------------
def show_images(images, epoch):
    images = images.detach().cpu()[:16]
    images = (images + 1) / 2   # Convert from [-1,1] to [0,1]
    images = images.squeeze(1)

    fig, axes = plt.subplots(4, 4, figsize=(6, 6))
    for i, ax in enumerate(axes.flatten()):
        ax.imshow(images[i], cmap="gray")
        ax.axis("off")

    plt.suptitle(f"Generated Images - Epoch {epoch+1}")
    plt.tight_layout()
    plt.show()


# -----------------------------
# Training Loop
# -----------------------------
for epoch in range(epochs):
    for real_images, _ in dataloader:
        real_images = real_images.to(device)
        current_batch_size = real_images.size(0)

        # Real and fake labels
        real_labels = torch.ones(current_batch_size, 1).to(device) * 0.9   # label smoothing
        fake_labels = torch.zeros(current_batch_size, 1).to(device)

        # -------------------------
        # Train Discriminator
        # -------------------------
        noise = torch.randn(current_batch_size, z_dim, 1, 1).to(device)
        fake_images = generator(noise)

        d_real = discriminator(real_images)
        loss_real = criterion(d_real, real_labels)

        d_fake = discriminator(fake_images.detach())
        loss_fake = criterion(d_fake, fake_labels)

        loss_d = loss_real + loss_fake

        optimizer_d.zero_grad()
        loss_d.backward()
        optimizer_d.step()

        # -------------------------
        # Train Generator
        # -------------------------
        output = discriminator(fake_images)
        loss_g = criterion(output, real_labels)

        optimizer_g.zero_grad()
        loss_g.backward()
        optimizer_g.step()

    print(f"Epoch [{epoch+1}/{epochs}]  Loss D: {loss_d.item():.4f}  Loss G: {loss_g.item():.4f}")
    show_images(fake_images, epoch)