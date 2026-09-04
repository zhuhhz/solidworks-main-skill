# License audit

This is an engineering reuse screen, not legal advice. It records GitHub repository metadata retrieved on 2026-09-03. Preserve notices whenever a license permits source reuse.

| Repository | SPDX | Classification | Practical consequence |
|---|---|---|---|
| `wzyn20051216/solidworks-automation-skill` | MIT | SAFE_TO_REUSE | Commercial use/modification permitted with copyright and license notice. Prefer adapter integration, not vendoring. |
| `lllssc/Drawing2CAD` | MIT | SAFE_TO_REUSE | Reuse only isolated compatible code with notice; current project needs architecture ideas, not its ML stack. |
| `Mohil-Ahuja/2D-to-3D-CAD-Reconstruction` | MIT | SAFE_TO_REUSE | Same MIT notice requirement; no need to import ML code. |
| `eyfel/mcp-server-solidworks` | AGPL-3.0-only | REFERENCE_ONLY | Network-service source-disclosure obligations make direct integration unsuitable for a proprietary/closed deployment. |
| `manycore-research/PlankAssembly` | AGPL-3.0-only | REFERENCE_ONLY | Do not copy model or rendering code into this project. |
| `elrinor/qrec` | NOASSERTION | UNKNOWN | No repository license was declared; copy no code. Algorithms/papers may be studied independently. |
| `KeNiu042/CReFT-CAD` | NOASSERTION | UNKNOWN | Dataset/code claims do not establish reuse rights. |
| `maowiz/step2pdf` | NOASSERTION | UNKNOWN | Do not copy source without an explicit license. |
| `getvenkateshprasad-sys/step-to-drawing` | NOASSERTION | UNKNOWN | Do not copy source without an explicit license. |
| `zarcherlot/q3ds-solidworks-mcp` | unavailable | UNKNOWN | GitHub API returned not found/unavailable; no reuse. |

`solidworks-main-skill` must keep external projects external. A successful technical experiment never changes license obligations.
