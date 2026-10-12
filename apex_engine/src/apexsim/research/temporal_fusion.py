"""Compact TFT ADAPTATION: past-only telemetry, static contexts and known horizon index."""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class GatedResidualNetwork(nn.Module):
    def __init__(self, inputs: int, hidden: int, outputs: int, context: int = 0, dropout: float = .1):
        super().__init__()
        self.first=nn.Linear(inputs,hidden)
        self.context=nn.Linear(context,hidden,bias=False) if context else None
        self.second=nn.Linear(hidden,outputs)
        self.gate=nn.Linear(outputs,2*outputs)
        self.skip=nn.Identity() if inputs==outputs else nn.Linear(inputs,outputs)
        self.dropout=nn.Dropout(dropout)
        self.norm=nn.LayerNorm(outputs)

    def forward(self, value: torch.Tensor, context: torch.Tensor | None = None) -> torch.Tensor:
        hidden=self.first(value)
        if self.context is not None and context is not None:
            hidden=hidden+self.context(context)
        hidden=self.second(F.elu(hidden))
        return self.norm(self.skip(value)+F.glu(self.gate(self.dropout(hidden)),dim=-1))


class VariableSelection(nn.Module):
    """Each variable has its own embedding/GRN; weights use flattened embeddings."""
    def __init__(self, widths: tuple[int,...], hidden: int, context: bool):
        super().__init__()
        self.widths=widths
        self.embeddings=nn.ModuleList(nn.Linear(width,hidden) for width in widths)
        self.transforms=nn.ModuleList(GatedResidualNetwork(hidden,hidden,hidden) for _ in widths)
        self.weights=GatedResidualNetwork(len(widths)*hidden,hidden,len(widths),hidden if context else 0)

    def forward(self, value: torch.Tensor, context: torch.Tensor | None = None) -> tuple[torch.Tensor,torch.Tensor]:
        pieces=torch.split(value,self.widths,dim=-1)
        embeddings=[layer(piece) for layer,piece in zip(self.embeddings,pieces,strict=True)]
        weights=torch.softmax(self.weights(torch.cat(embeddings,dim=-1),context),dim=-1)
        transformed=torch.stack([layer(embedding) for layer,embedding in zip(self.transforms,embeddings,strict=True)],dim=-2)
        return (transformed*weights.unsqueeze(-1)).sum(dim=-2),weights


class SharedValueAttention(nn.Module):
    """TFT interpretable attention averages heads with a shared value projection."""
    def __init__(self, hidden: int, heads: int = 2):
        super().__init__()
        if hidden%heads:
            raise ValueError("TFT hidden width must divide attention heads")
        self.width=hidden//heads
        self.queries=nn.ModuleList(nn.Linear(hidden,self.width) for _ in range(heads))
        self.keys=nn.ModuleList(nn.Linear(hidden,self.width) for _ in range(heads))
        self.values=nn.Linear(hidden,self.width)
        self.output=nn.Linear(self.width,hidden)

    def forward(self, value: torch.Tensor) -> tuple[torch.Tensor,torch.Tensor]:
        n=value.shape[1]
        mask=torch.triu(torch.ones(n,n,dtype=torch.bool,device=value.device),diagonal=1)
        shared=self.values(value)
        outputs,weights=[],[]
        for query,key in zip(self.queries,self.keys,strict=True):
            scores=query(value)@key(value).transpose(-2,-1)/self.width**.5
            attention=torch.softmax(scores.masked_fill(mask,float("-inf")),dim=-1)
            weights.append(attention)
            outputs.append(attention@shared)
        return self.output(torch.stack(outputs,dim=1).mean(dim=1)),torch.stack(weights,dim=1)


class TemporalFusionForecaster(nn.Module):
    """Four targets, ordered quantiles, direct1/3/5-step output without future controls."""
    def __init__(self, dynamic_features: int, static_widths: tuple[int,...], hidden: int = 16, history: int = 8):
        super().__init__()
        self.history,self.dynamic_features,self.static_widths=history,dynamic_features,static_widths
        self.static_selection=VariableSelection(static_widths,hidden,False)
        self.past_selection=VariableSelection((1,)*dynamic_features,hidden,True)
        self.contexts=nn.ModuleList(GatedResidualNetwork(hidden,hidden,hidden) for _ in range(4))
        self.future_embedding=nn.Linear(1,hidden)
        self.future_selection=VariableSelection((hidden,),hidden,True)
        self.encoder=nn.LSTM(hidden,hidden,batch_first=True)
        self.decoder=nn.LSTM(hidden,hidden,batch_first=True)
        self.local_gate=nn.Linear(hidden,2*hidden)
        self.local_norm=nn.LayerNorm(hidden)
        self.enrichment=GatedResidualNetwork(hidden,hidden,hidden,hidden)
        self.attention=SharedValueAttention(hidden)
        self.attention_gate=nn.Linear(hidden,2*hidden)
        self.attention_norm=nn.LayerNorm(hidden)
        self.position_grn=GatedResidualNetwork(hidden,hidden,hidden)
        self.final_gate=nn.Linear(hidden,2*hidden)
        self.final_norm=nn.LayerNorm(hidden)
        self.quantiles=nn.Linear(hidden,4*3)

    def forward(self, dynamic: torch.Tensor, static: torch.Tensor, diagnostics: bool = False):
        if (dynamic.ndim!=3 or dynamic.shape[1:]!=(self.history,self.dynamic_features)
                or static.shape!=(len(dynamic),sum(self.static_widths))):
            raise ValueError("TFT accepts fixed past history and static covariates only")
        context,static_weights=self.static_selection(static)
        selection,enrichment,cell,hidden=(layer(context) for layer in self.contexts)
        past,past_weights=self.past_selection(dynamic,selection[:,None,:])
        known=torch.arange(1,6,dtype=dynamic.dtype,device=dynamic.device)[None,:,None].expand(len(dynamic),-1,-1)/5
        future,_=self.future_selection(self.future_embedding(known),selection[:,None,:])
        encoded,(h,c)=self.encoder(past,(hidden[None],cell[None]))
        decoded,_=self.decoder(future,(h,c))
        local=self.local_norm(torch.cat((past,future),dim=1)+F.glu(self.local_gate(torch.cat((encoded,decoded),dim=1)),dim=-1))
        enriched=self.enrichment(local,enrichment[:,None,:])
        attended,attention=self.attention(enriched)
        attended=self.attention_norm(enriched+F.glu(self.attention_gate(attended),dim=-1))
        fused=self.final_norm(local+F.glu(self.final_gate(self.position_grn(attended)),dim=-1))
        raw=self.quantiles(fused[:,self.history:]).reshape(len(dynamic),5,4,3)
        center=raw[...,1]
        ordered=torch.stack((center-F.softplus(raw[...,0]),center,center+F.softplus(raw[...,2])),dim=-1)
        result=ordered[:,[0,2,4]]
        if diagnostics:
            return result,{"static_selection":static_weights,"past_selection":past_weights,"attention":attention}
        return result


class RecurrentForecaster(nn.Module):
    def __init__(self, kind: str, dynamic_features: int, static_widths: tuple[int,...], hidden: int = 16, history: int = 8):
        super().__init__()
        if kind not in ("gru","lstm"):
            raise ValueError("Unknown recurrent architecture")
        self.history=history
        self.recurrent=(nn.GRU if kind=="gru" else nn.LSTM)(dynamic_features,hidden,batch_first=True)
        self.head=nn.Sequential(nn.Linear(hidden+sum(static_widths),hidden),nn.ELU(),nn.Linear(hidden,12))

    def forward(self, dynamic: torch.Tensor, static: torch.Tensor) -> torch.Tensor:
        if dynamic.shape[1]!=self.history:
            raise ValueError("Recurrent model requires fixed past history")
        output,_=self.recurrent(dynamic)
        return self.head(torch.cat((output[:,-1],static),dim=-1)).reshape(len(dynamic),3,4)


def quantile_loss(prediction: torch.Tensor, actual: torch.Tensor) -> torch.Tensor:
    quantiles=torch.tensor([.1,.5,.9],dtype=prediction.dtype,device=prediction.device)
    error=actual.unsqueeze(-1)-prediction
    return torch.maximum(quantiles*error,(quantiles-1)*error).mean()
