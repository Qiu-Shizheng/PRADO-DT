"""Optional PyTorch implementation of the proposed condition-aware modules.

This file is imported only on a node with PyTorch.  A frozen scFM embedding
can be passed as ``cell_state``; the adapter itself is small enough for a GPU
10/205 node and can be trained with LoRA-style parameter freezing.
"""

import math

import torch
from torch import nn


class DoseTimeConditionEncoder(nn.Module):
    def __init__(self, n_perturbations, n_drugs, width=128, fourier_bands=4):
        super().__init__()
        self.pert = nn.Embedding(n_perturbations, width // 2)
        self.drug = nn.Embedding(n_drugs, width // 2)
        self.bands = nn.Parameter(torch.arange(1, fourier_bands + 1).float(),
                                  requires_grad=False)
        self.proj = nn.Sequential(
            nn.Linear(width + 2 * (1 + 2 * fourier_bands), width), nn.GELU(),
            nn.LayerNorm(width))

    def forward(self, perturbation, drug, dose, time):
        def fourier(z):
            # Dose exports use incompatible units (0/1/10 in GxE and
            # 10--10,000 nM in sciPlex3).  log1p keeps zero-dose controls
            # finite and prevents the condition encoder from treating a unit
            # change as a four-order-of-magnitude jump.
            z = torch.log1p(z.clamp_min(0.0)).unsqueeze(-1)
            f = z * self.bands.to(z.device)
            return torch.cat([z, torch.sin(f), torch.cos(f)], dim=-1)
        cond = torch.cat([self.pert(perturbation), self.drug(drug),
                           fourier(dose), fourier(time)], dim=-1)
        return self.proj(cond)


class ContextAdapter(nn.Module):
    """FiLM adapter for an untreated/context embedding."""
    def __init__(self, state_dim, condition_dim, width=128):
        super().__init__()
        self.state = nn.Linear(state_dim, width)
        self.context = nn.Linear(state_dim, width)
        self.film = nn.Linear(condition_dim, 2 * width)

    def forward(self, cell_state, control_state, condition):
        h = self.state(cell_state) + self.context(control_state)
        gamma, beta = self.film(condition).chunk(2, dim=-1)
        return torch.tanh(gamma) * h + beta


class DynamicResponseHead(nn.Module):
    def __init__(self, width, output_dim):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(width + 4, width), nn.GELU(),
                                 nn.Linear(width, 2 * output_dim))

    def forward(self, h, dose, time):
        # Keep the kinetic basis invariant to the dose unit.  The old raw
        # dose and dose*time terms made a 10,000 nM export numerically
        # unstable even when the same biological schedule was represented as
        # 10 in another H5AD.
        dose_log = torch.log1p(dose.clamp_min(0.0))
        time_rel = time / 24.0
        kinetic = torch.cat([time_rel.unsqueeze(-1), torch.exp(-time_rel.unsqueeze(-1)),
                             dose_log.unsqueeze(-1), (dose_log * time_rel).unsqueeze(-1)], dim=-1)
        mean, logvar = self.net(torch.cat([h, kinetic], dim=-1)).chunk(2, dim=-1)
        # Bound the variance head before exponentiation in the NLL.  The
        # previous lower bound allowed exp(-logvar) to reach ~3,000 on the
        # first batch, making the heteroscedastic ablation numerically
        # unstable on sparse single-cell targets.
        return mean, logvar.clamp(-3.0, 3.0)


class PRADODTModel(nn.Module):
    """PRADO-DT condition-aware response model with heteroscedastic uncertainty."""
    def __init__(self, state_dim, output_dim, n_perturbations, n_drugs,
                 width=128):
        super().__init__()
        self.condition = DoseTimeConditionEncoder(n_perturbations, n_drugs,
                                                   width=width)
        self.adapter = ContextAdapter(state_dim, width, width=width)
        self.head = DynamicResponseHead(width, output_dim)

    def forward(self, cell_state, control_state, perturbation, drug, dose, time):
        c = self.condition(perturbation, drug, dose, time)
        h = self.adapter(cell_state, control_state, c)
        return self.head(h, dose, time)

    @staticmethod
    def heteroscedastic_loss(mean, logvar, target):
        precision = torch.exp(-logvar)
        return (precision * (target - mean).pow(2) + logvar).mean()


class InvariantResidualModel(PRADODTModel):
    """Predict a context-invariant treatment response and add it to control.

    This is the explicit structural version of ``--residual`` in the training
    script.  The untreated state is an anchor shared across domains while the
    condition network only models the intervention response.  That separation
    is useful under leave-one-cell-line-out evaluation: a new line contributes
    its control profile, while the perturbation/dose response is transferred
    from source lines.  ``residual`` is kept in the public name because it is
    the quantity used by the loss and by the conformal interval.
    """

    def __init__(self, state_dim, output_dim, n_perturbations, n_drugs,
                 width=128):
        super().__init__(state_dim, output_dim, n_perturbations, n_drugs,
                         width=width)
        # A small linear anchor prevents the correction head from having to
        # reproduce the high-dimensional untreated profile.
        self.anchor = nn.Linear(state_dim, output_dim)
        self.correction = nn.Sequential(
            nn.Linear(width + 4, width), nn.GELU(),
            nn.LayerNorm(width), nn.Linear(width, 2 * output_dim))

    def forward(self, cell_state, control_state, perturbation, drug, dose,
                time):
        condition = self.condition(perturbation, drug, dose, time)
        h = self.adapter(cell_state, control_state, condition)
        dose_log = torch.log1p(dose.clamp_min(0.0))
        time_rel = time / 24.0
        kinetic = torch.cat((time_rel.unsqueeze(-1),
                             torch.exp(-time_rel.unsqueeze(-1)),
                             dose_log.unsqueeze(-1),
                             (dose_log * time_rel).unsqueeze(-1)), dim=-1)
        delta, logvar = self.correction(torch.cat((h, kinetic), dim=-1)).chunk(2, dim=-1)
        # The anchor is the untreated/context state.  Returning the full
        # response keeps this class compatible with the existing evaluator;
        # the training entry point can subtract the anchor for residual loss.
        return self.anchor(control_state) + delta, logvar.clamp(-3.0, 3.0)


class LowRankInteractionModel(PRADODTModel):
    """Low-rank GxE interaction head for sparse perturbation screens.

    A condition-dependent rank-r factorization maps the shared context to
    gene responses.  It constrains the cross-product of perturbation, drug and
    dose to a low-dimensional response manifold, which is a useful inductive
    bias when most gene-by-condition cells are unobserved.
    """

    def __init__(self, state_dim, output_dim, n_perturbations, n_drugs,
                 width=128, rank=32):
        super().__init__(state_dim, output_dim, n_perturbations, n_drugs,
                         width=width)
        self.rank = int(rank)
        self.factor = nn.Sequential(nn.Linear(width + state_dim, width),
                                    nn.GELU(), nn.Linear(width, rank))
        self.gene_factor = nn.Parameter(torch.empty(output_dim, rank))
        self.gene_bias = nn.Parameter(torch.zeros(output_dim))
        self.control_anchor = (nn.Identity() if state_dim == output_dim
                               else nn.Linear(state_dim, output_dim))
        nn.init.normal_(self.gene_factor, std=0.02)
        self.scale = nn.Linear(width + 4, 2)

    def forward(self, cell_state, control_state, perturbation, drug, dose,
                time):
        condition = self.condition(perturbation, drug, dose, time)
        h = self.adapter(cell_state, control_state, condition)
        z = self.factor(torch.cat((h, control_state), dim=-1))
        delta = torch.matmul(z, self.gene_factor.t()) + self.gene_bias
        dose_log = torch.log1p(dose.clamp_min(0.0))
        time_rel = time / 24.0
        kinetic = torch.cat((time_rel.unsqueeze(-1),
                             torch.exp(-time_rel.unsqueeze(-1)),
                             dose_log.unsqueeze(-1),
                             (dose_log * time_rel).unsqueeze(-1)), dim=-1)
        scale = self.scale(torch.cat((h, kinetic), dim=-1))
        # A positive scale keeps the rank-r correction numerically bounded and
        # lets the model learn dose/time attenuation without a dense head.
        mean = torch.tanh(scale[:, :1]) * delta
        logvar = scale[:, 1:2].expand_as(mean).clamp(-3.0, 3.0)
        return mean + self.control_anchor(control_state), logvar


class MixtureResponseModel(PRADODTModel):
    """Two-component response head for heterogeneous cell states.

    The mixture is intentionally small: component means are full gene vectors
    and the gating probability is conditioned on the cell/context state.  The
    evaluator uses the mixture mean, while ``mixture_nll`` can train the model
    when response modes (sensitive/resistant cells) are expected.
    """

    def __init__(self, state_dim, output_dim, n_perturbations, n_drugs,
                 width=128, components=2):
        super().__init__(state_dim, output_dim, n_perturbations, n_drugs,
                         width=width)
        self.components = int(components)
        self.mix = nn.Linear(width, components)
        self.means = nn.ModuleList(
            [nn.Sequential(nn.Linear(width + 4, width), nn.GELU(),
                           nn.Linear(width, output_dim))
             for _ in range(self.components)])
        self.control_anchor = (nn.Identity() if state_dim == output_dim
                               else nn.Linear(state_dim, output_dim))

    def _features(self, h, dose, time):
        dose_log = torch.log1p(dose.clamp_min(0.0))
        time_rel = time / 24.0
        kinetic = torch.cat((time_rel.unsqueeze(-1),
                             torch.exp(-time_rel.unsqueeze(-1)),
                             dose_log.unsqueeze(-1),
                             (dose_log * time_rel).unsqueeze(-1)), dim=-1)
        return torch.cat((h, kinetic), dim=-1)

    def forward(self, cell_state, control_state, perturbation, drug, dose,
                time, return_components=False):
        condition = self.condition(perturbation, drug, dose, time)
        h = self.adapter(cell_state, control_state, condition)
        features = self._features(h, dose, time)
        anchor = self.control_anchor(control_state)
        means = torch.stack([head(features) + anchor
                             for head in self.means], dim=1)
        logits = self.mix(h)
        weights = torch.softmax(logits, dim=-1)
        mean = (weights.unsqueeze(-1) * means).sum(dim=1)
        logvar = torch.zeros_like(mean)
        if return_components:
            return mean, logvar, means, logits
        return mean, logvar

    @staticmethod
    def mixture_nll(means, logits, target, variance=1.0):
        """Gaussian mixture NLL with a fixed observation variance."""
        var = float(variance)
        sq = (target.unsqueeze(1) - means).pow(2).mean(dim=-1)
        log_prob = -0.5 * sq / var - 0.5 * math.log(2.0 * math.pi * var)
        return -torch.logsumexp(torch.log_softmax(logits, dim=-1) + log_prob,
                                dim=-1).mean()
