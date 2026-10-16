"""Stack placeholder del andamiaje CDK (tarea 11.1).

Existe solo para que ``cdk synth`` produzca una plantilla CloudFormation válida
y así verificar, sin credenciales ni recursos reales, que el tooling (AWS CDK)
y el proyecto Python compilan y sintetizan. No crea ningún recurso.

La tarea 11.2 lo sustituye por los stacks reales (`NetworkStack`, `DataStack`,
`ComputeStack`, `AiIamStack`) descritos en ``docs/cloud/cdk.md``.
"""

from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from constructs import Construct


class PlaceholderStack(Stack):
    """Stack vacío de verificación del andamiaje (sin recursos AWS)."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Una salida informativa deja la plantilla no-vacía y documenta el
        # estado del andamiaje. No provisiona infraestructura.
        CfnOutput(
            self,
            "AndamiajeEstado",
            value="tarea-11.1-scaffolding-ok",
            description=(
                "Marca de verificación: el proyecto CDK de jAImes sintetiza. "
                "Los stacks reales se añaden en la tarea 11.2."
            ),
        )
