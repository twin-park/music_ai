# 귀 모델: 로그 멜 → CNN → (소리 묶음 확률, 말투 감정)
import torch
import torch.nn as nn
import torch.nn.functional as F
from features import LogMel, N_MELS
from labels import N_GROUPS, EMOTIONS


class Block(nn.Module):
    def __init__(self, ci, co, pool):
        super().__init__()
        self.c1 = nn.Conv2d(ci, co, 3, padding=1, bias=False)
        self.b1 = nn.BatchNorm2d(co)
        self.c2 = nn.Conv2d(co, co, 3, padding=1, bias=False)
        self.b2 = nn.BatchNorm2d(co)
        self.pool = pool

    def forward(self, x):
        x = F.relu(self.b1(self.c1(x)))
        x = F.relu(self.b2(self.c2(x)))
        return F.avg_pool2d(x, self.pool) if self.pool else x


class Ear(nn.Module):
    def __init__(self, width=64, n_blocks=4):
        super().__init__()
        self.mel = LogMel()
        self.bn0 = nn.BatchNorm2d(N_MELS)
        ch = [1] + [width * 2 ** i for i in range(n_blocks)]
        self.blocks = nn.ModuleList(Block(ch[i], ch[i + 1], (2, 2)) for i in range(n_blocks))
        d = ch[-1]
        self.fc = nn.Linear(d, d)
        self.att = nn.Conv1d(d, N_GROUPS, 1)      # 소리 묶음: 시간축 주의 풀링
        self.cla = nn.Conv1d(d, N_GROUPS, 1)
        self.emo_att = nn.Conv1d(d, 1, 1)         # 감정: 말소리 구간에 집중
        self.emo = nn.Linear(d, len(EMOTIONS))
        self.drop = nn.Dropout(0.2)

    def embed(self, logmel):
        x = logmel.unsqueeze(1)                    # (B,1,M,T)
        x = self.bn0(x.transpose(1, 2)).transpose(1, 2)
        for b in self.blocks:
            x = b(x)
        x = x.mean(2)                              # 주파수 평균 → (B,C,T')
        x = F.relu(self.fc(self.drop(x).transpose(1, 2))).transpose(1, 2)
        return x

    def heads(self, h):
        att = torch.softmax(torch.clamp(self.att(h), -10, 10), dim=-1)
        frame = self.cla(h)                        # 로짓 (B,G,T')
        clip = (att * torch.sigmoid(frame)).sum(-1).clamp(1e-6, 1 - 1e-6)
        ea = torch.softmax(self.emo_att(h), dim=-1)
        emo = self.emo(self.drop((ea * h).sum(-1)))
        return clip, emo, torch.sigmoid(frame)

    def forward(self, logmel):
        return self.heads(self.embed(logmel))
