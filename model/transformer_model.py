import math

import torch
from torch import Tensor
import torch.nn as nn
from torch.nn import TransformerEncoder, TransformerEncoderLayer

from .mixture_of_softmaxes import MixtureOfSoftmaxes


class TransformerModel(nn.Module):
    def __init__(self, ntoken: int, ninp: int = 512, nhead: int = 8,
                 nhid: int = 2048, nlayers: int = 6, dropout: float = 0.5, num_softmaxes: int = 1):
        super(TransformerModel, self).__init__()
        self.model_type = 'Transformer'
        self.pos_encoder = PositionalEncoding(ninp, dropout)
        encoder_layers = TransformerEncoderLayer(ninp, nhead, nhid, dropout)
        self.transformer_encoder = TransformerEncoder(encoder_layers, nlayers)
        self.encoder = nn.Embedding(ntoken, ninp)
        self.ninp = ninp

        # Set up decoder
        if num_softmaxes == 1:
            self.decoder = nn.Sequential(
                nn.Linear(ninp, ntoken), nn.LogSoftmax(dim=-1))
        elif num_softmaxes > 1:
            self.decoder = MixtureOfSoftmaxes(
                num_softmaxes, ntoken, ninp, dropout)
        else:
            raise Exception("num_softmaxes needs to be greater than 0")

        self.init_weights()

    def generate_square_subsequent_mask(self, sz: int) -> Tensor:
        mask = (torch.triu(torch.ones(sz, sz)) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float(
            '-inf')).masked_fill(mask == 1, float(0.0))
        return mask

    def init_weights(self) -> None:
        initrange = 0.1
        self.encoder.weight.data.uniform_(-initrange, initrange)

        def init_decoder(module):
            if isinstance(module, nn.Linear):
                module.bias.data.zero_()
                module.weight.data.uniform_(-initrange, initrange)

        self.decoder.apply(init_decoder)

    def forward(self, src: Tensor, src_mask: Tensor) -> Tensor:
        src = self.encoder(src) * math.sqrt(self.ninp)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src, src_mask)
        output = self.decoder(output)
        return output


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(
            0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x: Tensor) -> Tensor:
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)
